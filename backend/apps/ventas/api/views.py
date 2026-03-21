from datetime import date, timedelta

from django.db import IntegrityError
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.core.services import SecuenciaService
from apps.core.models import TipoDocumento
from apps.core.exceptions import BusinessRuleError

from apps.ventas.api.filters import (
    FacturaVentaFilter,
    GuiaDespachoFilter,
    NotaCreditoVentaFilter,
    PedidoVentaFilter,
)
from apps.ventas.api.serializers import (
    FacturaVentaItemSerializer,
    FacturaVentaSerializer,
    GuiaDespachoItemSerializer,
    GuiaDespachoSerializer,
    NotaCreditoVentaItemSerializer,
    NotaCreditoVentaSerializer,
    PedidoVentaItemSerializer,
    PedidoVentaSerializer,
    VentaHistorialSerializer,
)
from apps.ventas.models import (
    EstadoFacturaVenta,
    FacturaVenta,
    FacturaVentaItem,
    GuiaDespacho,
    GuiaDespachoItem,
    NotaCreditoVenta,
    NotaCreditoVentaItem,
    PedidoVenta,
    PedidoVentaItem,
    TipoDocumentoVenta,
    VentaHistorial,
)
from apps.ventas.services import (
    FacturaVentaService,
    GuiaDespachoService,
    NotaCreditoVentaService,
    PedidoVentaService,
)
from apps.presupuestos.services.presupuesto_service import PresupuestoService


class VentasAuditoriaMixin:
    """Utilidades comunes de auditoría para views del módulo ventas."""

    def _registrar_auditoria(self, empresa, usuario, action_code, entity_type, entity_id, summary, changes=None):
        from apps.auditoria.services import AuditoriaService
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="VENTAS",
            action_code=action_code,
            event_type=f"ventas.{action_code.lower()}",
            entity_type=entity_type,
            entity_id=str(entity_id),
            summary=summary,
            changes=changes,
        )


# ─── Pedido de Venta ──────────────────────────────────────────────────────────

class PedidoVentaViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD y flujo de estados de pedidos de venta."""

    serializer_class = PedidoVentaSerializer
    model = PedidoVenta
    filterset_class = PedidoVentaFilter
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "duplicar": Acciones.CREAR,
        "historial": Acciones.VER,
        "siguiente_numero": Acciones.CREAR,
    }

    def get_queryset(self):
        return super().get_queryset().select_related("cliente__contacto", "lista_precio", "presupuesto_origen")

    def perform_create(self, serializer):
        self._set_tenant_context()
        empresa = self.get_empresa()
        usuario = self.request.user
        datos = serializer.validated_data
        PedidoVentaService.crear_pedido(datos=datos, empresa=empresa, usuario=usuario)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._set_tenant_context()
        empresa = self.get_empresa()
        presupuesto_origen = serializer.validated_data.get("presupuesto_origen")
        if presupuesto_origen:
            if presupuesto_origen.empresa_id != empresa.id:
                raise BusinessRuleError("El presupuesto origen no pertenece a la empresa activa.")
            PresupuestoService.validar_presupuesto_disponible_para_documento(
                presupuesto=presupuesto_origen,
            )
        pedido = PedidoVentaService.crear_pedido(
            datos=serializer.validated_data,
            empresa=empresa,
            usuario=request.user,
        )
        return Response(
            PedidoVentaSerializer(pedido, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        PedidoVentaService.eliminar_pedido(
            pedido_id=self.get_object().id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """Confirma pedido BORRADOR→CONFIRMADO y reserva stock."""
        self._set_tenant_context()
        pedido = PedidoVentaService.confirmar_pedido(
            pedido_id=pk, empresa=self.get_empresa(), usuario=request.user
        )
        return Response(PedidoVentaSerializer(pedido, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        """Anula pedido y libera reservas de stock."""
        self._set_tenant_context()
        motivo = request.data.get("motivo", "")
        pedido = PedidoVentaService.anular_pedido(
            pedido_id=pk, empresa=self.get_empresa(), usuario=request.user, motivo=motivo
        )
        return Response(PedidoVentaSerializer(pedido, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        """Clona pedido con nuevo folio en estado BORRADOR."""
        self._set_tenant_context()
        pedido = PedidoVentaService.duplicar_pedido(
            pedido_id=pk, empresa=self.get_empresa(), usuario=request.user
        )
        return Response(
            PedidoVentaSerializer(pedido, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def siguiente_numero(self, request):
        """Retorna el próximo folio a asignar sin persistirlo."""
        self._set_tenant_context()
        numero = SecuenciaService.obtener_numero_siguiente_disponible(
            self.get_empresa(), TipoDocumento.PEDIDO_VENTA
        )
        return Response({"numero": numero})

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        """Retorna el historial de cambios de estado del pedido."""
        qs = VentaHistorial.all_objects.filter(
            empresa=self.get_empresa(),
            tipo_documento=TipoDocumentoVenta.PEDIDO,
            documento_id=pk,
        ).order_by("-creado_en")
        return Response(VentaHistorialSerializer(qs, many=True).data)


class PedidoVentaItemViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD de líneas de pedido de venta."""

    serializer_class = PedidoVentaItemSerializer
    model = PedidoVentaItem
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.EDITAR,
    }

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "impuesto", "presupuesto_item_origen")
        pedido_id = self.request.query_params.get("pedido_venta")
        if pedido_id:
            qs = qs.filter(pedido_venta_id=pedido_id)
        return qs

    def _validar_pedido_editable(self):
        pedido_id = self.request.data.get("pedido_venta") or (
            self.get_object().pedido_venta_id if self.kwargs.get("pk") else None
        )
        if hasattr(pedido_id, "id"):
            pedido_id = pedido_id.id
        if pedido_id:
            empresa = self.get_empresa()
            pedido = PedidoVenta.objects.filter(pk=pedido_id, empresa=empresa).first()
            if pedido:
                PedidoVentaService.validar_editable(pedido=pedido)

    def perform_create(self, serializer):
        self._set_tenant_context()
        self._validar_pedido_editable()
        pedido = serializer.validated_data.get("pedido_venta")
        presupuesto_item_origen = serializer.validated_data.get("presupuesto_item_origen")
        if presupuesto_item_origen:
            PresupuestoService.validar_consumo_item_presupuesto(
                presupuesto_item=presupuesto_item_origen,
                cantidad_solicitada=serializer.validated_data.get("cantidad"),
                empresa=self.get_empresa(),
                presupuesto_origen=pedido.presupuesto_origen,
            )
        item = serializer.save()
        PedidoVentaService.recalcular_totales(pedido=item.pedido_venta)

    def perform_update(self, serializer):
        self._set_tenant_context()
        item_actual = self.get_object()
        PedidoVentaService.validar_editable(pedido=item_actual.pedido_venta)
        presupuesto_item_origen = serializer.validated_data.get(
            "presupuesto_item_origen",
            item_actual.presupuesto_item_origen,
        )
        if presupuesto_item_origen:
            PresupuestoService.validar_consumo_item_presupuesto(
                presupuesto_item=presupuesto_item_origen,
                cantidad_solicitada=serializer.validated_data.get("cantidad", item_actual.cantidad),
                empresa=self.get_empresa(),
                presupuesto_origen=item_actual.pedido_venta.presupuesto_origen,
                excluir={"pedido_item_id": item_actual.id},
            )
        item = serializer.save()
        PedidoVentaService.recalcular_totales(pedido=item.pedido_venta)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        PedidoVentaService.validar_editable(pedido=instance.pedido_venta)
        pedido = instance.pedido_venta
        instance.delete()
        PedidoVentaService.recalcular_totales(pedido=pedido)


def _parse_date_param(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise DRFValidationError({field_name: ["Debe usar formato YYYY-MM-DD."]}) from exc


def _analytics_grouping_expression(grouping, field_name):
    if grouping == "semanal":
        return TruncWeek(field_name)
    return TruncMonth(field_name)


def _serialize_period(value):
    if not value:
        return None
    if hasattr(value, "date"):
        return value.date().isoformat()
    return value.isoformat()


# ─── Guía de Despacho ─────────────────────────────────────────────────────────

class GuiaDespachoViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD y flujo de estados de guías de despacho."""

    serializer_class = GuiaDespachoSerializer
    model = GuiaDespacho
    filterset_class = GuiaDespachoFilter
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "siguiente_numero": Acciones.CREAR,
        "historial": Acciones.VER,
    }

    def get_queryset(self):
        return super().get_queryset().select_related("cliente__contacto", "pedido_venta", "bodega")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._set_tenant_context()
        guia = GuiaDespachoService.crear_guia(
            datos=serializer.validated_data,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(
            GuiaDespachoSerializer(guia, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        guia = self.get_object()
        GuiaDespachoService.validar_editable(guia=guia)
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Valida que la guía siga editable antes de persistir cambios de cabecera."""
        self._set_tenant_context()
        GuiaDespachoService.validar_editable(guia=self.get_object())
        serializer.save()

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """Confirma guía BORRADOR→CONFIRMADA y registra salida en inventario."""
        self._set_tenant_context()
        bodega_id = request.data.get("bodega_id")
        guia = GuiaDespachoService.confirmar_guia(
            guia_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
            bodega_id=bodega_id,
        )
        return Response(GuiaDespachoSerializer(guia, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        """Anula guía confirmada con movimiento compensatorio en inventario."""
        self._set_tenant_context()
        bodega_id = request.data.get("bodega_id")
        motivo = request.data.get("motivo", "")
        guia = GuiaDespachoService.anular_guia(
            guia_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
            bodega_id=bodega_id,
            motivo=motivo,
        )
        return Response(GuiaDespachoSerializer(guia, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def siguiente_numero(self, request):
        """Retorna el próximo folio de guía de despacho sin persistirlo."""
        self._set_tenant_context()
        numero = SecuenciaService.obtener_numero_siguiente_disponible(
            self.get_empresa(), TipoDocumento.GUIA_DESPACHO
        )
        return Response({"numero": numero})

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        """Retorna el historial de cambios de estado de la guía."""
        qs = VentaHistorial.all_objects.filter(
            empresa=self.get_empresa(),
            tipo_documento=TipoDocumentoVenta.GUIA,
            documento_id=pk,
        ).order_by("-creado_en")
        return Response(VentaHistorialSerializer(qs, many=True).data)


class GuiaDespachoItemViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD de líneas de guía de despacho."""

    serializer_class = GuiaDespachoItemSerializer
    model = GuiaDespachoItem
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.EDITAR,
    }

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "impuesto", "pedido_item")
        guia_id = self.request.query_params.get("guia_despacho")
        if guia_id:
            qs = qs.filter(guia_despacho_id=guia_id)
        return qs

    def _validar_guia_editable_desde_item(self, data=None, instance=None):
        guia_id = (data or {}).get("guia_despacho") or (instance.guia_despacho_id if instance else None)
        if hasattr(guia_id, "id"):
            guia_id = guia_id.id
        if guia_id:
            guia = GuiaDespacho.objects.filter(pk=guia_id, empresa=self.get_empresa()).first()
            if guia:
                GuiaDespachoService.validar_editable(guia=guia)

    def perform_create(self, serializer):
        self._set_tenant_context()
        self._validar_guia_editable_desde_item(data=serializer.validated_data)
        item = serializer.save()
        GuiaDespachoService.recalcular_totales(guia=item.guia_despacho)

    def perform_update(self, serializer):
        self._set_tenant_context()
        GuiaDespachoService.validar_editable(guia=self.get_object().guia_despacho)
        item = serializer.save()
        GuiaDespachoService.recalcular_totales(guia=item.guia_despacho)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        GuiaDespachoService.validar_editable(guia=instance.guia_despacho)
        guia = instance.guia_despacho
        instance.delete()
        GuiaDespachoService.recalcular_totales(guia=guia)


# ─── Factura de Venta ─────────────────────────────────────────────────────────

class FacturaVentaViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD y flujo de estados de facturas de venta."""

    serializer_class = FacturaVentaSerializer
    model = FacturaVenta
    filterset_class = FacturaVentaFilter
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "emitir": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "siguiente_numero": Acciones.CREAR,
        "historial": Acciones.VER,
        "resumen_operativo": Acciones.VER,
        "analytics": Acciones.VER,
    }

    def get_queryset(self):
        return super().get_queryset().select_related(
            "cliente__contacto", "pedido_venta", "guia_despacho", "presupuesto_origen"
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._set_tenant_context()
        presupuesto_origen = serializer.validated_data.get("presupuesto_origen")
        if presupuesto_origen:
            if presupuesto_origen.empresa_id != self.get_empresa().id:
                raise BusinessRuleError("El presupuesto origen no pertenece a la empresa activa.")
            PresupuestoService.validar_presupuesto_disponible_para_documento(
                presupuesto=presupuesto_origen,
            )
        factura = FacturaVentaService.crear_factura(
            datos=serializer.validated_data,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(
            FacturaVentaSerializer(factura, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        factura = self.get_object()
        FacturaVentaService.validar_editable(factura=factura)
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Valida que la factura siga editable antes de persistir cambios de cabecera."""
        self._set_tenant_context()
        FacturaVentaService.validar_editable(factura=self.get_object())
        serializer.save()

    @action(detail=True, methods=["post"])
    def emitir(self, request, pk=None):
        """Emite factura BORRADOR→EMITIDA y genera cuenta por cobrar."""
        self._set_tenant_context()
        factura = FacturaVentaService.emitir_factura(
            factura_id=pk, empresa=self.get_empresa(), usuario=request.user
        )
        return Response(FacturaVentaSerializer(factura, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        """Anula factura EMITIDA y genera nota de crédito de anulación automática."""
        self._set_tenant_context()
        motivo = request.data.get("motivo", "")
        factura = FacturaVentaService.anular_factura(
            factura_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
            motivo=motivo,
        )
        return Response(FacturaVentaSerializer(factura, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def siguiente_numero(self, request):
        """Retorna el próximo folio de factura sin persistirlo."""
        self._set_tenant_context()
        numero = SecuenciaService.obtener_numero_siguiente_disponible(
            self.get_empresa(), TipoDocumento.FACTURA_VENTA
        )
        return Response({"numero": numero})

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        """Retorna el historial de cambios de estado de la factura."""
        qs = VentaHistorial.all_objects.filter(
            empresa=self.get_empresa(),
            tipo_documento=TipoDocumentoVenta.FACTURA,
            documento_id=pk,
        ).order_by("-creado_en")
        return Response(VentaHistorialSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def resumen_operativo(self, request):
        """Retorna metricas operativas simples para seguimiento comercial de facturas."""
        self._set_tenant_context()
        hoy = timezone.localdate()
        agregados = self.get_queryset().aggregate(
            total_documentos=Count("id"),
            monto_total=Sum("total"),
            monto_emitido=Sum("total", filter=Q(estado=EstadoFacturaVenta.EMITIDA)),
            monto_vencido=Sum(
                "total",
                filter=Q(
                    estado=EstadoFacturaVenta.EMITIDA,
                    fecha_vencimiento__lt=hoy,
                ),
            ),
            monto_por_vencer_7_dias=Sum(
                "total",
                filter=Q(
                    estado=EstadoFacturaVenta.EMITIDA,
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=hoy + timedelta(days=7),
                ),
            ),
            borradores=Count("id", filter=Q(estado=EstadoFacturaVenta.BORRADOR)),
            emitidas=Count("id", filter=Q(estado=EstadoFacturaVenta.EMITIDA)),
            anuladas=Count("id", filter=Q(estado=EstadoFacturaVenta.ANULADA)),
            vencidas=Count(
                "id",
                filter=Q(
                    estado=EstadoFacturaVenta.EMITIDA,
                    fecha_vencimiento__lt=hoy,
                ),
            ),
            por_vencer_7_dias=Count(
                "id",
                filter=Q(
                    estado=EstadoFacturaVenta.EMITIDA,
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=hoy + timedelta(days=7),
                ),
            ),
        )
        return Response(
            {
                "fecha_corte": hoy,
                "total_documentos": agregados["total_documentos"] or 0,
                "monto_total": agregados["monto_total"] or 0,
                "monto_emitido": agregados["monto_emitido"] or 0,
                "monto_vencido": agregados["monto_vencido"] or 0,
                "monto_por_vencer_7_dias": agregados["monto_por_vencer_7_dias"] or 0,
                "borradores": agregados["borradores"] or 0,
                "emitidas": agregados["emitidas"] or 0,
                "anuladas": agregados["anuladas"] or 0,
                "vencidas": agregados["vencidas"] or 0,
                "por_vencer_7_dias": agregados["por_vencer_7_dias"] or 0,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Retorna analitica filtrable para reportes profesionales de facturas."""
        self._set_tenant_context()
        queryset = self.get_queryset()
        fecha_desde = _parse_date_param(request.query_params.get("fecha_desde"), "fecha_desde")
        fecha_hasta = _parse_date_param(request.query_params.get("fecha_hasta"), "fecha_hasta")
        cliente = request.query_params.get("cliente")
        estado = request.query_params.get("estado")
        cartera = request.query_params.get("cartera") or "ALL"
        agrupacion = request.query_params.get("agrupacion") or "mensual"
        hoy = timezone.localdate()

        if fecha_desde:
            queryset = queryset.filter(fecha_emision__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
        if cliente:
            queryset = queryset.filter(cliente__contacto__nombre=cliente)
        if estado and estado != "ALL":
            queryset = queryset.filter(estado=estado)
        if cartera == "VENCIDAS":
            queryset = queryset.filter(estado=EstadoFacturaVenta.EMITIDA, fecha_vencimiento__lt=hoy)
        elif cartera == "POR_VENCER_7_DIAS":
            queryset = queryset.filter(
                estado=EstadoFacturaVenta.EMITIDA,
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=hoy + timedelta(days=7),
            )
        elif cartera == "BORRADORES":
            queryset = queryset.filter(estado=EstadoFacturaVenta.BORRADOR)

        metrics = queryset.aggregate(
            total_facturas=Count("id"),
            facturacion_total=Sum("total"),
            monto_emitido=Sum("total", filter=Q(estado=EstadoFacturaVenta.EMITIDA)),
            emitidas=Count("id", filter=Q(estado=EstadoFacturaVenta.EMITIDA)),
            borradores=Count("id", filter=Q(estado=EstadoFacturaVenta.BORRADOR)),
            anuladas=Count("id", filter=Q(estado=EstadoFacturaVenta.ANULADA)),
            vencidas=Count("id", filter=Q(estado=EstadoFacturaVenta.EMITIDA, fecha_vencimiento__lt=hoy)),
            monto_vencido=Sum("total", filter=Q(estado=EstadoFacturaVenta.EMITIDA, fecha_vencimiento__lt=hoy)),
            por_vencer=Count(
                "id",
                filter=Q(
                    estado=EstadoFacturaVenta.EMITIDA,
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=hoy + timedelta(days=7),
                ),
            ),
            monto_por_vencer=Sum(
                "total",
                filter=Q(
                    estado=EstadoFacturaVenta.EMITIDA,
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=hoy + timedelta(days=7),
                ),
            ),
        )

        top_clientes = list(
            queryset.values("cliente_id", "cliente__contacto__nombre")
            .annotate(total=Sum("total"))
            .order_by("-total")[:5]
        )

        series = list(
            queryset.annotate(periodo=_analytics_grouping_expression(agrupacion, "fecha_emision"))
            .values("periodo")
            .annotate(cantidad=Count("id"), monto=Sum("total"))
            .order_by("periodo")
        )

        detail = list(
            queryset.order_by("-fecha_emision", "-creado_en").values(
                "id",
                "numero",
                "cliente_id",
                "cliente__contacto__nombre",
                "fecha_emision",
                "fecha_vencimiento",
                "estado",
                "total",
            )
        )

        top_productos = list(
            FacturaVentaItem.objects.filter(empresa=self.get_empresa(), factura_venta__in=queryset)
            .annotate(
                line_total=ExpressionWrapper(
                    F("cantidad") * F("precio_unitario"),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
            .values("producto_id", "descripcion")
            .annotate(
                cantidad=Sum("cantidad"),
                monto=Sum("line_total"),
            )
            .order_by("-monto")[:5]
        )

        vencidos = list(
            queryset.filter(estado=EstadoFacturaVenta.EMITIDA, fecha_vencimiento__lt=hoy)
            .order_by("fecha_vencimiento")
            .values(
                "id",
                "numero",
                "cliente__contacto__nombre",
                "fecha_vencimiento",
                "total",
            )[:10]
        )

        return Response(
            {
                "filters": {
                    "fecha_desde": fecha_desde,
                    "fecha_hasta": fecha_hasta,
                    "cliente": cliente or "",
                    "estado": estado or "ALL",
                    "cartera": cartera,
                    "agrupacion": agrupacion,
                    "fecha_corte": hoy,
                },
                "metrics": {
                    "total_facturas": metrics["total_facturas"] or 0,
                    "facturacion_total": metrics["facturacion_total"] or 0,
                    "monto_emitido": metrics["monto_emitido"] or 0,
                    "emitidas": metrics["emitidas"] or 0,
                    "borradores": metrics["borradores"] or 0,
                    "anuladas": metrics["anuladas"] or 0,
                    "vencidas": metrics["vencidas"] or 0,
                    "monto_vencido": metrics["monto_vencido"] or 0,
                    "por_vencer": metrics["por_vencer"] or 0,
                    "monto_por_vencer": metrics["monto_por_vencer"] or 0,
                },
                "top_clientes": [
                    {
                        "cliente_id": row["cliente_id"],
                        "nombre": row["cliente__contacto__nombre"] or "-",
                        "total": row["total"] or 0,
                    }
                    for row in top_clientes
                ],
                "top_productos": [
                    {
                        "producto_id": row["producto_id"],
                        "nombre": row["descripcion"] or f"Producto {row['producto_id'] or '-'}",
                        "cantidad": row["cantidad"] or 0,
                        "monto": row["monto"] or 0,
                    }
                    for row in top_productos
                ],
                "series": [
                    {
                        "periodo": _serialize_period(row["periodo"]),
                        "cantidad": row["cantidad"] or 0,
                        "monto": row["monto"] or 0,
                    }
                    for row in series
                ],
                "documentos_vencidos": [
                    {
                        "id": row["id"],
                        "numero": row["numero"],
                        "cliente_nombre": row["cliente__contacto__nombre"] or "-",
                        "fecha_vencimiento": row["fecha_vencimiento"],
                        "total": row["total"] or 0,
                    }
                    for row in vencidos
                ],
                "detail": [
                    {
                        "id": row["id"],
                        "numero": row["numero"],
                        "cliente_id": row["cliente_id"],
                        "cliente_nombre": row["cliente__contacto__nombre"] or "-",
                        "fecha_emision": row["fecha_emision"],
                        "fecha_vencimiento": row["fecha_vencimiento"],
                        "estado": row["estado"],
                        "total": row["total"] or 0,
                    }
                    for row in detail
                ],
            },
            status=status.HTTP_200_OK,
        )


class FacturaVentaItemViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD de líneas de factura de venta."""

    serializer_class = FacturaVentaItemSerializer
    model = FacturaVentaItem
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.EDITAR,
    }

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "impuesto", "guia_item", "presupuesto_item_origen")
        factura_id = self.request.query_params.get("factura_venta")
        if factura_id:
            qs = qs.filter(factura_venta_id=factura_id)
        return qs

    def perform_create(self, serializer):
        self._set_tenant_context()
        factura = FacturaVenta.objects.filter(
            pk=serializer.validated_data.get("factura_venta").id,
            empresa=self.get_empresa(),
        ).first()
        if factura:
            FacturaVentaService.validar_editable(factura=factura)
        presupuesto_item_origen = serializer.validated_data.get("presupuesto_item_origen")
        if presupuesto_item_origen and factura:
            PresupuestoService.validar_consumo_item_presupuesto(
                presupuesto_item=presupuesto_item_origen,
                cantidad_solicitada=serializer.validated_data.get("cantidad"),
                empresa=self.get_empresa(),
                presupuesto_origen=factura.presupuesto_origen,
            )
        item = serializer.save()
        FacturaVentaService.recalcular_totales(factura=item.factura_venta)

    def perform_update(self, serializer):
        self._set_tenant_context()
        item_actual = self.get_object()
        FacturaVentaService.validar_editable(factura=item_actual.factura_venta)
        presupuesto_item_origen = serializer.validated_data.get(
            "presupuesto_item_origen",
            item_actual.presupuesto_item_origen,
        )
        if presupuesto_item_origen:
            PresupuestoService.validar_consumo_item_presupuesto(
                presupuesto_item=presupuesto_item_origen,
                cantidad_solicitada=serializer.validated_data.get("cantidad", item_actual.cantidad),
                empresa=self.get_empresa(),
                presupuesto_origen=item_actual.factura_venta.presupuesto_origen,
                excluir={"factura_item_id": item_actual.id},
            )
        item = serializer.save()
        FacturaVentaService.recalcular_totales(factura=item.factura_venta)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        FacturaVentaService.validar_editable(factura=instance.factura_venta)
        factura = instance.factura_venta
        instance.delete()
        FacturaVentaService.recalcular_totales(factura=factura)


# ─── Nota de Crédito de Venta ─────────────────────────────────────────────────

class NotaCreditoVentaViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD y flujo de estados de notas de crédito de venta."""

    serializer_class = NotaCreditoVentaSerializer
    model = NotaCreditoVenta
    filterset_class = NotaCreditoVentaFilter
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "emitir": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "siguiente_numero": Acciones.CREAR,
        "historial": Acciones.VER,
    }

    def get_queryset(self):
        return super().get_queryset().select_related(
            "cliente__contacto", "factura_origen"
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._set_tenant_context()
        nota = NotaCreditoVentaService.crear_nota_credito(
            datos=serializer.validated_data,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(
            NotaCreditoVentaSerializer(nota, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        nota = self.get_object()
        NotaCreditoVentaService.validar_editable(nota=nota)
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        """Valida que la nota siga editable antes de persistir cambios de cabecera."""
        self._set_tenant_context()
        NotaCreditoVentaService.validar_editable(nota=self.get_object())
        serializer.save()

    @action(detail=True, methods=["post"])
    def emitir(self, request, pk=None):
        """Emite nota de crédito BORRADOR→EMITIDA y aplica crédito en cartera."""
        self._set_tenant_context()
        nota = NotaCreditoVentaService.emitir_nota_credito(
            nota_id=pk, empresa=self.get_empresa(), usuario=request.user
        )
        return Response(NotaCreditoVentaSerializer(nota, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        """Anula nota de crédito EMITIDA."""
        self._set_tenant_context()
        motivo = request.data.get("motivo", "")
        nota = NotaCreditoVentaService.anular_nota_credito(
            nota_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
            motivo=motivo,
        )
        return Response(NotaCreditoVentaSerializer(nota, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def siguiente_numero(self, request):
        """Retorna el próximo folio de nota de crédito sin persistirlo."""
        self._set_tenant_context()
        numero = SecuenciaService.obtener_numero_siguiente_disponible(
            self.get_empresa(), TipoDocumento.NOTA_CREDITO_VENTA
        )
        return Response({"numero": numero})

    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None):
        """Retorna el historial de cambios de estado de la nota de crédito."""
        qs = VentaHistorial.all_objects.filter(
            empresa=self.get_empresa(),
            tipo_documento=TipoDocumentoVenta.NOTA_CREDITO,
            documento_id=pk,
        ).order_by("-creado_en")
        return Response(VentaHistorialSerializer(qs, many=True).data)


class NotaCreditoVentaItemViewSet(VentasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    """CRUD de líneas de nota de crédito de venta."""

    serializer_class = NotaCreditoVentaItemSerializer
    model = NotaCreditoVentaItem
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.EDITAR,
    }

    def get_queryset(self):
        qs = super().get_queryset().select_related("producto", "impuesto", "factura_item")
        nota_id = self.request.query_params.get("nota_credito")
        if nota_id:
            qs = qs.filter(nota_credito_id=nota_id)
        return qs

    def perform_create(self, serializer):
        self._set_tenant_context()
        nota = serializer.validated_data.get("nota_credito")
        if nota:
            NotaCreditoVentaService.validar_editable(nota=nota)
        item = serializer.save()
        NotaCreditoVentaService.recalcular_totales(nota=item.nota_credito)

    def perform_update(self, serializer):
        self._set_tenant_context()
        NotaCreditoVentaService.validar_editable(nota=self.get_object().nota_credito)
        item = serializer.save()
        NotaCreditoVentaService.recalcular_totales(nota=item.nota_credito)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        NotaCreditoVentaService.validar_editable(nota=instance.nota_credito)
        nota = instance.nota_credito
        instance.delete()
        NotaCreditoVentaService.recalcular_totales(nota=nota)
