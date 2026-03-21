from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth, TruncWeek
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.compras.api.serializer import (
    DocumentoCompraProveedorItemSerializer,
    DocumentoCompraProveedorSerializer,
    OrdenCompraItemSerializer,
    OrdenCompraSerializer,
    RecepcionCompraItemSerializer,
    RecepcionCompraSerializer,
)
from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    EstadoOrdenCompra,
    OrdenCompra,
    OrdenCompraItem,
    EstadoRecepcion,
    RecepcionCompra,
    RecepcionCompraItem,
)
from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.compras.services import DocumentoCompraService, OrdenCompraService, RecepcionCompraService
from apps.core.exceptions import AuthorizationError, ConflictError
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.core.models import TipoDocumento
from apps.core.services import SecuenciaService


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


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "sí"}


class ComprasAuditoriaMixin:
    """Registra eventos de auditoria para operaciones CRUD del modulo Compras."""

    @staticmethod
    def _build_auditoria_meta(instance):
        return {
            "source": "compras.api.views",
            "entity_model": instance.__class__.__name__,
            "entity_pk": str(getattr(instance, "pk", "") or ""),
        }

    @staticmethod
    def _choice_display(instance, field_name):
        getter = getattr(instance, f"get_{field_name}_display", None)
        if callable(getter):
            return getter()
        return None

    def _build_auditoria_payload(self, instance):
        payload = {
            "model": instance.__class__.__name__,
            "empresa_id": str(getattr(instance, "empresa_id", "") or ""),
        }

        if hasattr(instance, "numero") and getattr(instance, "numero", None) is not None:
            payload["numero"] = str(instance.numero)
        if hasattr(instance, "folio") and getattr(instance, "folio", None):
            payload["folio"] = str(instance.folio)
        if hasattr(instance, "serie") and getattr(instance, "serie", None):
            payload["serie"] = str(instance.serie)
        if hasattr(instance, "tipo_documento") and getattr(instance, "tipo_documento", None):
            payload["tipo_documento"] = str(instance.tipo_documento)
            tipo_label = self._choice_display(instance, "tipo_documento")
            if tipo_label:
                payload["tipo_documento_label"] = tipo_label
        if hasattr(instance, "estado") and getattr(instance, "estado", None):
            payload["estado"] = str(instance.estado)
            estado_label = self._choice_display(instance, "estado")
            if estado_label:
                payload["estado_label"] = estado_label

        return payload

    def _registrar_auditoria_compras(self, *, instance, action_code, event_type, summary, severity=AuditSeverity.INFO, changes=None):
        AuditoriaService.registrar_evento(
            empresa=instance.empresa,
            usuario=self.request.user,
            module_code=Modulos.COMPRAS,
            action_code=action_code,
            event_type=event_type,
            entity_type=instance.__class__.__name__.upper(),
            entity_id=str(instance.pk or ""),
            summary=summary,
            severity=severity,
            changes=changes or {},
            payload=self._build_auditoria_payload(instance),
            meta=self._build_auditoria_meta(instance),
            source="compras.api.views",
        )


class OrdenCompraViewSet(ComprasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    model = OrdenCompra
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "siguiente_numero": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "enviar": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "eliminar_sin_documentos": Acciones.BORRAR,
        "corregir": Acciones.EDITAR,
        "duplicar": Acciones.CREAR,
        "trazabilidad": Acciones.VER,
        "resumen_operativo": Acciones.VER,
        "analytics": Acciones.VER,
    }

    @staticmethod
    def _is_numero_oc_unique_error(error):
        message = str(error).lower()
        return (
            "unique_numero_oc_por_empresa" in message
            or "already exists" in message and "numero" in message and "empresa" in message
            or "ya existe" in message and "numero" in message and "empresa" in message
            or ("ordencompra" in message and "numero" in message and "empresa" in message)
            or ("orden compra" in message and "numero" in message and "empresa" in message)
        )

    def perform_update(self, serializer):
        self._set_tenant_context()
        OrdenCompraService.validar_orden_editable(orden=self.get_object())
        serializer.save()
        self._registrar_auditoria_compras(
            instance=serializer.instance,
            action_code=Acciones.EDITAR,
            event_type="OC_ACTUALIZADA",
            summary=f"Orden de compra #{serializer.instance.numero} actualizada.",
        )

    def perform_create(self, serializer):
        """Asigna numero secuencial y reintenta si encuentra uno ya ocupado."""
        max_attempts = 5
        for _ in range(max_attempts):
            numero_siguiente = SecuenciaService.obtener_siguiente_numero(
                empresa=self.request.user.empresa_activa,
                tipo_documento=TipoDocumento.ORDEN_COMPRA,
            )
            try:
                serializer.save(
                    numero=numero_siguiente,
                    empresa=self.request.user.empresa_activa,
                    creado_por=self.request.user,
                    estado="BORRADOR",
                )
                self._registrar_auditoria_compras(
                    instance=serializer.instance,
                    action_code=Acciones.CREAR,
                    event_type="OC_CREADA",
                    summary=f"Orden de compra #{serializer.instance.numero} creada.",
                )
                return
            except (IntegrityError, DjangoValidationError, DRFValidationError) as exc:
                if self._is_numero_oc_unique_error(exc):
                    continue
                raise

        raise ConflictError(
            "No fue posible asignar un numero de orden disponible. Intente nuevamente."
        )

    def perform_destroy(self, instance):
        OrdenCompraService.validar_orden_editable(orden=instance)
        summary = f"Orden de compra #{instance.numero} eliminada."
        pk = instance.pk
        empresa = instance.empresa
        payload = self._build_auditoria_payload(instance)
        meta = self._build_auditoria_meta(instance)
        instance.delete()
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=self.request.user,
            module_code=Modulos.COMPRAS,
            action_code=Acciones.BORRAR,
            event_type="OC_ELIMINADA",
            entity_type="ORDENCOMPRA",
            entity_id=str(pk),
            summary=summary,
            severity=AuditSeverity.WARNING,
            payload=payload,
            meta=meta,
            source="compras.api.views",
        )

    @action(detail=False, methods=["get"])
    def siguiente_numero(self, request):
        numero = SecuenciaService.obtener_numero_siguiente_disponible(
            empresa=request.user.empresa_activa,
            tipo_documento=TipoDocumento.ORDEN_COMPRA,
        )
        return Response({"numero": numero}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def enviar(self, request, pk=None):
        orden = OrdenCompraService.enviar_orden(orden_id=pk, empresa=request.user.empresa_activa)
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        orden = OrdenCompraService.anular_orden(orden_id=pk, empresa=request.user.empresa_activa)
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def eliminar_sin_documentos(self, request, pk=None):
        OrdenCompraService.eliminar_orden_sin_documentos(orden_id=pk, empresa=request.user.empresa_activa)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def corregir(self, request, pk=None):
        motivo = request.data.get("motivo")
        orden = OrdenCompraService.corregir_orden(
            orden_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            motivo=motivo,
        )
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        orden = OrdenCompraService.duplicar_orden(
            orden_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
        )
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def trazabilidad(self, request, pk=None):
        orden = self.get_object()

        recepciones = (
            RecepcionCompra.all_objects.filter(empresa=orden.empresa, orden_compra=orden)
            .order_by("-fecha", "-creado_en")
        )
        documentos = (
            DocumentoCompraProveedor.all_objects.filter(empresa=orden.empresa, orden_compra=orden)
            .order_by("-fecha_emision", "-creado_en")
        )

        recepcion_ids = {str(recepcion.id) for recepcion in recepciones}

        data = {
            "orden_compra": {
                "id": str(orden.id),
                "numero": orden.numero,
                "estado": orden.estado,
                "fecha_emision": orden.fecha_emision,
                "fecha_entrega": orden.fecha_entrega,
                "proveedor_id": str(orden.proveedor_id),
                "total": orden.total,
            },
            "resumen": {
                "recepciones_total": len(recepciones),
                "recepciones_confirmadas": sum(1 for recepcion in recepciones if recepcion.estado == EstadoRecepcion.CONFIRMADA),
                "documentos_total": len(documentos),
                "documentos_confirmados": sum(1 for documento in documentos if documento.estado == EstadoDocumentoCompra.CONFIRMADO),
                "documentos_con_recepcion": sum(
                    1 for documento in documentos if documento.recepcion_compra_id and str(documento.recepcion_compra_id) in recepcion_ids
                ),
            },
            "recepciones": [
                {
                    "id": str(recepcion.id),
                    "fecha": recepcion.fecha,
                    "estado": recepcion.estado,
                    "observaciones": recepcion.observaciones,
                }
                for recepcion in recepciones
            ],
            "documentos": [
                {
                    "id": str(documento.id),
                    "tipo_documento": documento.tipo_documento,
                    "folio": documento.folio,
                    "serie": documento.serie,
                    "estado": documento.estado,
                    "fecha_emision": documento.fecha_emision,
                    "fecha_recepcion": documento.fecha_recepcion,
                    "total": documento.total,
                    "recepcion_compra_id": str(documento.recepcion_compra_id) if documento.recepcion_compra_id else None,
                    "documento_origen_id": str(documento.documento_origen_id) if documento.documento_origen_id else None,
                }
                for documento in documentos
            ],
        }

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def resumen_operativo(self, request):
        """Retorna metricas base para seguimiento operativo del abastecimiento."""
        self._set_tenant_context()
        agregados = self.get_queryset().aggregate(
            total_ordenes=Count("id"),
            monto_total=Sum("total"),
            borrador=Count("id", filter=Q(estado=EstadoOrdenCompra.BORRADOR)),
            enviadas=Count("id", filter=Q(estado=EstadoOrdenCompra.ENVIADA)),
            parciales=Count("id", filter=Q(estado=EstadoOrdenCompra.PARCIAL)),
            recibidas=Count("id", filter=Q(estado=EstadoOrdenCompra.RECIBIDA)),
            canceladas=Count("id", filter=Q(estado=EstadoOrdenCompra.CANCELADA)),
            monto_pendiente=Sum(
                "total",
                filter=Q(estado__in=[EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.PARCIAL]),
            ),
            pendientes_recepcion=Count(
                "id",
                filter=Q(estado__in=[EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.PARCIAL]),
            ),
        )
        return Response(
            {
                "total_ordenes": agregados["total_ordenes"] or 0,
                "monto_total": agregados["monto_total"] or 0,
                "borrador": agregados["borrador"] or 0,
                "enviadas": agregados["enviadas"] or 0,
                "parciales": agregados["parciales"] or 0,
                "recibidas": agregados["recibidas"] or 0,
                "canceladas": agregados["canceladas"] or 0,
                "monto_pendiente": agregados["monto_pendiente"] or 0,
                "pendientes_recepcion": agregados["pendientes_recepcion"] or 0,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Retorna analitica filtrable para reportes de ordenes de compra."""
        self._set_tenant_context()
        queryset = self.get_queryset().select_related("proveedor__contacto")
        fecha_desde = _parse_date_param(request.query_params.get("fecha_desde"), "fecha_desde")
        fecha_hasta = _parse_date_param(request.query_params.get("fecha_hasta"), "fecha_hasta")
        proveedor_id = request.query_params.get("proveedor_id")
        estado = request.query_params.get("estado")
        agrupacion = request.query_params.get("agrupacion") or "mensual"

        if fecha_desde:
            queryset = queryset.filter(fecha_emision__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        if estado and estado != "ALL":
            queryset = queryset.filter(estado=estado)

        metrics = queryset.aggregate(
            total_ordenes=Count("id"),
            monto_comprometido=Sum("total"),
            pendientes_recepcion=Count("id", filter=Q(estado__in=[EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.PARCIAL])),
            enviadas=Count("id", filter=Q(estado=EstadoOrdenCompra.ENVIADA)),
            parciales=Count("id", filter=Q(estado=EstadoOrdenCompra.PARCIAL)),
            recibidas=Count("id", filter=Q(estado=EstadoOrdenCompra.RECIBIDA)),
        )

        top_proveedores = list(
            queryset.values("proveedor_id", "proveedor__contacto__nombre")
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
                "fecha_emision",
                "estado",
                "total",
                "proveedor_id",
                "proveedor__contacto__nombre",
            )
        )

        top_productos = list(
            OrdenCompraItem.objects.filter(empresa=self.get_empresa(), orden_compra__in=queryset)
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

        return Response(
            {
                "filters": {
                    "fecha_desde": fecha_desde,
                    "fecha_hasta": fecha_hasta,
                    "proveedor_id": proveedor_id,
                    "estado": estado or "ALL",
                    "agrupacion": agrupacion,
                },
                "metrics": {
                    "total_ordenes": metrics["total_ordenes"] or 0,
                    "monto_comprometido": metrics["monto_comprometido"] or 0,
                    "pendientes_recepcion": metrics["pendientes_recepcion"] or 0,
                    "enviadas": metrics["enviadas"] or 0,
                    "parciales": metrics["parciales"] or 0,
                    "recibidas": metrics["recibidas"] or 0,
                },
                "top_proveedores": [
                    {
                        "proveedor_id": row["proveedor_id"],
                        "nombre": row["proveedor__contacto__nombre"] or "-",
                        "total": row["total"] or 0,
                    }
                    for row in top_proveedores
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
                "detail": [
                    {
                        "id": row["id"],
                        "numero": row["numero"],
                        "fecha_emision": row["fecha_emision"],
                        "estado": row["estado"],
                        "total": row["total"] or 0,
                        "proveedor_id": row["proveedor_id"],
                        "proveedor_nombre": row["proveedor__contacto__nombre"] or "-",
                    }
                    for row in detail
                ],
            },
            status=status.HTTP_200_OK,
        )


class OrdenCompraItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = OrdenCompraItem
    serializer_class = OrdenCompraItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    def _get_orden_from_request_or_instance(self, instance=None):
        if instance is not None:
            return instance.orden_compra
        orden_id = self.request.data.get("orden_compra")
        if not orden_id:
            return None
        return OrdenCompra.all_objects.filter(id=orden_id, empresa=self.request.user.empresa_activa).first()

    def perform_create(self, serializer):
        self._set_tenant_context()
        orden = self._get_orden_from_request_or_instance()
        if orden:
            OrdenCompraService.validar_orden_editable(orden=orden)
        item = serializer.save()
        OrdenCompraService.recalcular_totales(orden=item.orden_compra)

    def perform_update(self, serializer):
        self._set_tenant_context()
        OrdenCompraService.validar_orden_editable(orden=self.get_object().orden_compra)
        item = serializer.save()
        OrdenCompraService.recalcular_totales(orden=item.orden_compra)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        OrdenCompraService.validar_orden_editable(orden=instance.orden_compra)
        orden = instance.orden_compra
        instance.delete()
        OrdenCompraService.recalcular_totales(orden=orden)


class DocumentoCompraProveedorViewSet(ComprasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    model = DocumentoCompraProveedor
    serializer_class = DocumentoCompraProveedorSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar_guia": Acciones.APROBAR,
        "confirmar_factura": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "corregir": Acciones.EDITAR,
        "duplicar": Acciones.CREAR,
        "resumen_operativo": Acciones.VER,
        "analytics": Acciones.VER,
    }

    def perform_update(self, serializer):
        self._set_tenant_context()
        DocumentoCompraService.validar_documento_editable(documento=self.get_object())
        serializer.save()
        self._registrar_auditoria_compras(
            instance=serializer.instance,
            action_code=Acciones.EDITAR,
            event_type="DOCUMENTO_COMPRA_ACTUALIZADO",
            summary="Documento de compra actualizado.",
        )

    def perform_create(self, serializer):
        self._set_tenant_context()
        instance = serializer.save(estado=EstadoDocumentoCompra.BORRADOR)
        DocumentoCompraService.avanzar_orden_si_borrador(documento=instance)
        DocumentoCompraService.recalcular_totales(documento=instance)
        self._registrar_auditoria_compras(
            instance=instance,
            action_code=Acciones.CREAR,
            event_type="DOCUMENTO_COMPRA_CREADO",
            summary="Documento de compra creado.",
        )

    def perform_destroy(self, instance):
        self._set_tenant_context()
        DocumentoCompraService.validar_documento_editable(documento=instance)
        pk = instance.pk
        empresa = instance.empresa
        payload = self._build_auditoria_payload(instance)
        meta = self._build_auditoria_meta(instance)
        instance.delete()
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=self.request.user,
            module_code=Modulos.COMPRAS,
            action_code=Acciones.BORRAR,
            event_type="DOCUMENTO_COMPRA_ELIMINADO",
            entity_type="DOCUMENTOCOMPRAPROVEEDOR",
            entity_id=str(pk),
            summary="Documento de compra eliminado.",
            severity=AuditSeverity.WARNING,
            payload=payload,
            meta=meta,
            source="compras.api.views",
        )

    @action(detail=True, methods=["post"])
    def confirmar_guia(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        en_transito = _as_bool(request.data.get("en_transito"))
        documento = DocumentoCompraService.confirmar_guia(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
            en_transito=en_transito,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def confirmar_factura(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        en_transito = _as_bool(request.data.get("en_transito"))
        documento = DocumentoCompraService.confirmar_factura(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
            en_transito=en_transito,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        documento = DocumentoCompraService.anular_documento(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def corregir(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        motivo = request.data.get("motivo")
        documento = DocumentoCompraService.corregir_documento(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            motivo=motivo,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        documento = DocumentoCompraService.duplicar_documento(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def resumen_operativo(self, request):
        """Retorna metricas base de documentos de compra para control documental."""
        agregados = self.get_queryset().aggregate(
            total_documentos=Count("id"),
            monto_total=Sum("total"),
            monto_confirmado=Sum("total", filter=Q(estado=EstadoDocumentoCompra.CONFIRMADO)),
            borradores=Count("id", filter=Q(estado=EstadoDocumentoCompra.BORRADOR)),
            confirmados=Count("id", filter=Q(estado=EstadoDocumentoCompra.CONFIRMADO)),
            anulados=Count("id", filter=Q(estado=EstadoDocumentoCompra.ANULADO)),
            guias=Count("id", filter=Q(tipo_documento="GUIA_RECEPCION")),
            facturas=Count("id", filter=Q(tipo_documento="FACTURA_COMPRA")),
            boletas=Count("id", filter=Q(tipo_documento="BOLETA_COMPRA")),
            sin_recepcion=Count(
                "id",
                filter=Q(estado=EstadoDocumentoCompra.CONFIRMADO, recepcion_compra__isnull=True),
            ),
        )
        return Response(
            {
                "total_documentos": agregados["total_documentos"] or 0,
                "monto_total": agregados["monto_total"] or 0,
                "monto_confirmado": agregados["monto_confirmado"] or 0,
                "borradores": agregados["borradores"] or 0,
                "confirmados": agregados["confirmados"] or 0,
                "anulados": agregados["anulados"] or 0,
                "guias": agregados["guias"] or 0,
                "facturas": agregados["facturas"] or 0,
                "boletas": agregados["boletas"] or 0,
                "sin_recepcion": agregados["sin_recepcion"] or 0,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Retorna analitica filtrable para reportes documentales de compras."""
        self._set_tenant_context()
        queryset = self.get_queryset().select_related("proveedor__contacto")
        fecha_desde = _parse_date_param(request.query_params.get("fecha_desde"), "fecha_desde")
        fecha_hasta = _parse_date_param(request.query_params.get("fecha_hasta"), "fecha_hasta")
        proveedor_id = request.query_params.get("proveedor_id")
        estado = request.query_params.get("estado")
        tipo = request.query_params.get("tipo_documento")
        agrupacion = request.query_params.get("agrupacion") or "mensual"

        if fecha_desde:
            queryset = queryset.filter(fecha_emision__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_emision__lte=fecha_hasta)
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
        if estado and estado != "ALL":
            queryset = queryset.filter(estado=estado)
        if tipo and tipo != "ALL":
            queryset = queryset.filter(tipo_documento=tipo)

        metrics = queryset.aggregate(
            total_documentos=Count("id"),
            monto_documental=Sum("total"),
            monto_confirmado=Sum("total", filter=Q(estado=EstadoDocumentoCompra.CONFIRMADO)),
            pendientes_documentales=Count("id", filter=Q(estado=EstadoDocumentoCompra.BORRADOR)),
            facturas=Count("id", filter=Q(tipo_documento="FACTURA_COMPRA")),
            guias=Count("id", filter=Q(tipo_documento="GUIA_RECEPCION")),
            boletas=Count("id", filter=Q(tipo_documento="BOLETA_COMPRA")),
        )

        top_proveedores = list(
            queryset.values("proveedor_id", "proveedor__contacto__nombre")
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
                "tipo_documento",
                "folio",
                "fecha_emision",
                "estado",
                "total",
                "proveedor_id",
                "proveedor__contacto__nombre",
            )
        )

        top_productos = list(
            DocumentoCompraProveedorItem.objects.filter(empresa=self.get_empresa(), documento__in=queryset)
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

        return Response(
            {
                "filters": {
                    "fecha_desde": fecha_desde,
                    "fecha_hasta": fecha_hasta,
                    "proveedor_id": proveedor_id,
                    "estado": estado or "ALL",
                    "tipo_documento": tipo or "ALL",
                    "agrupacion": agrupacion,
                },
                "metrics": {
                    "total_documentos": metrics["total_documentos"] or 0,
                    "monto_documental": metrics["monto_documental"] or 0,
                    "monto_confirmado": metrics["monto_confirmado"] or 0,
                    "pendientes_documentales": metrics["pendientes_documentales"] or 0,
                    "facturas": metrics["facturas"] or 0,
                    "guias": metrics["guias"] or 0,
                    "boletas": metrics["boletas"] or 0,
                },
                "top_proveedores": [
                    {
                        "proveedor_id": row["proveedor_id"],
                        "nombre": row["proveedor__contacto__nombre"] or "-",
                        "total": row["total"] or 0,
                    }
                    for row in top_proveedores
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
                "detail": [
                    {
                        "id": row["id"],
                        "tipo_documento": row["tipo_documento"],
                        "folio": row["folio"],
                        "fecha_emision": row["fecha_emision"],
                        "estado": row["estado"],
                        "total": row["total"] or 0,
                        "proveedor_id": row["proveedor_id"],
                        "proveedor_nombre": row["proveedor__contacto__nombre"] or "-",
                    }
                    for row in detail
                ],
            },
            status=status.HTTP_200_OK,
        )


class DocumentoCompraProveedorItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = DocumentoCompraProveedorItem
    serializer_class = DocumentoCompraProveedorItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        documento_id = self.request.query_params.get("documento")
        if documento_id:
            queryset = queryset.filter(documento_id=documento_id)
        return queryset

    def perform_create(self, serializer):
        self._set_tenant_context()
        documento = serializer.validated_data["documento"]
        empresa_id = getattr(self.request.user.empresa_activa, "id", None)
        if empresa_id and documento.empresa_id != empresa_id:
            raise AuthorizationError("No tiene permisos sobre el documento seleccionado.")
        if documento.estado != EstadoDocumentoCompra.BORRADOR:
            raise ConflictError("Solo se pueden agregar items en documentos en borrador.")
        item = serializer.save()
        DocumentoCompraService.recalcular_totales(documento=item.documento)

    def perform_update(self, serializer):
        self._set_tenant_context()
        documento = serializer.instance.documento
        empresa_id = getattr(self.request.user.empresa_activa, "id", None)
        if empresa_id and documento.empresa_id != empresa_id:
            raise AuthorizationError("No tiene permisos sobre el documento seleccionado.")
        if documento.estado != EstadoDocumentoCompra.BORRADOR:
            raise ConflictError("Solo se pueden editar items en documentos en borrador.")
        item = serializer.save()
        DocumentoCompraService.recalcular_totales(documento=item.documento)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        if instance.documento.estado != EstadoDocumentoCompra.BORRADOR:
            raise ConflictError("Solo se pueden eliminar items en documentos en borrador.")
        documento = instance.documento
        instance.delete()
        DocumentoCompraService.recalcular_totales(documento=documento)


class RecepcionCompraViewSet(ComprasAuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    model = RecepcionCompra
    serializer_class = RecepcionCompraSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar": Acciones.APROBAR,
    }

    def perform_create(self, serializer):
        self._set_tenant_context()
        serializer.save(estado=EstadoRecepcion.BORRADOR)
        self._registrar_auditoria_compras(
            instance=serializer.instance,
            action_code=Acciones.CREAR,
            event_type="RECEPCION_CREADA",
            summary="Recepcion de compra creada.",
        )

    def perform_update(self, serializer):
        self._set_tenant_context()
        RecepcionCompraService.validar_recepcion_editable(recepcion=self.get_object())
        serializer.save()
        self._registrar_auditoria_compras(
            instance=serializer.instance,
            action_code=Acciones.EDITAR,
            event_type="RECEPCION_ACTUALIZADA",
            summary="Recepcion de compra actualizada.",
        )

    def perform_destroy(self, instance):
        self._set_tenant_context()
        RecepcionCompraService.validar_recepcion_editable(recepcion=instance)
        pk = instance.pk
        empresa = instance.empresa
        payload = self._build_auditoria_payload(instance)
        meta = self._build_auditoria_meta(instance)
        instance.delete()
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=self.request.user,
            module_code=Modulos.COMPRAS,
            action_code=Acciones.BORRAR,
            event_type="RECEPCION_ELIMINADA",
            entity_type="RECEPCIONCOMPRA",
            entity_id=str(pk),
            summary="Recepcion de compra eliminada.",
            severity=AuditSeverity.WARNING,
            payload=payload,
            meta=meta,
            source="compras.api.views",
        )

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        recepcion = RecepcionCompraService.confirmar_recepcion(
            recepcion_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=request.data.get("bodega_id"),
        )
        serializer = self.get_serializer(recepcion)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecepcionCompraItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = RecepcionCompraItem
    serializer_class = RecepcionCompraItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    def perform_create(self, serializer):
        self._set_tenant_context()
        recepcion = serializer.validated_data["recepcion"]
        if recepcion.estado != EstadoRecepcion.BORRADOR:
            raise ConflictError("Solo se pueden agregar items en recepciones en borrador.")
        orden_item = serializer.validated_data.get("orden_item")
        if recepcion.orden_compra_id and not orden_item:
            raise ConflictError("Debe indicar orden_item cuando la recepcion esta asociada a una OC.")
        if orden_item and recepcion.orden_compra_id and orden_item.orden_compra_id != recepcion.orden_compra_id:
            raise ConflictError("El orden_item no pertenece a la OC de la recepcion.")
        serializer.save()

    def perform_update(self, serializer):
        self._set_tenant_context()
        if serializer.instance.recepcion.estado != EstadoRecepcion.BORRADOR:
            raise ConflictError("Solo se pueden editar items en recepciones en borrador.")
        serializer.save()

    def perform_destroy(self, instance):
        self._set_tenant_context()
        if instance.recepcion.estado != EstadoRecepcion.BORRADOR:
            raise ConflictError("Solo se pueden eliminar items en recepciones en borrador.")
        instance.delete()
