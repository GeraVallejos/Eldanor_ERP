from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.exceptions import BusinessRuleError, ResourceNotFoundError
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.tesoreria.api.serializers import (
    AplicarPagoSerializer,
    ConciliarMovimientoBancarioSerializer,
    ConvertirMontoSerializer,
    CuentaBancariaEmpresaSerializer,
    CuentaPorCobrarSerializer,
    CuentaPorPagarSerializer,
    MonedaSerializer,
    MovimientoBancarioSerializer,
    TipoCambioSerializer,
)
from apps.tesoreria.models import (
    CuentaBancariaEmpresa,
    CuentaPorCobrar,
    CuentaPorPagar,
    Moneda,
    MovimientoBancario,
    TipoCambio,
)
from apps.tesoreria.services import (
    CarteraService,
    TesoreriaBancariaService,
    TipoCambioService,
    build_movimientos_bancarios_template,
    import_movimientos_bancarios,
)


def _aging_bucket_label(dias):
    if dias <= 0:
        return "al_dia"
    if dias <= 30:
        return "1_30"
    if dias <= 60:
        return "31_60"
    if dias <= 90:
        return "61_90"
    return "91_plus"


class TipoCambioViewSet(TenantViewSetMixin, ModelViewSet):
    model = TipoCambio
    serializer_class = TipoCambioSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.TESORERIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONCILIAR,
        "update": Acciones.CONCILIAR,
        "partial_update": Acciones.CONCILIAR,
        "destroy": Acciones.CONCILIAR,
        "convertir": Acciones.VER,
    }

    @action(detail=False, methods=["post"])
    def convertir(self, request):
        self._set_tenant_context()
        serializer = ConvertirMontoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        monto = TipoCambioService.convertir_monto(
            empresa=self.get_empresa(),
            monto=data["monto"],
            moneda_origen=data["moneda_origen"],
            moneda_destino=data["moneda_destino"],
            fecha=data.get("fecha"),
            decimales=data.get("decimales", 2),
        )
        return Response({"monto_convertido": monto}, status=status.HTTP_200_OK)


class MonedaViewSet(TenantViewSetMixin, ModelViewSet):
    model = Moneda
    serializer_class = MonedaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.TESORERIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONCILIAR,
        "update": Acciones.CONCILIAR,
        "partial_update": Acciones.CONCILIAR,
        "destroy": Acciones.CONCILIAR,
    }


class CuentaBancariaEmpresaViewSet(TenantViewSetMixin, ModelViewSet):
    model = CuentaBancariaEmpresa
    serializer_class = CuentaBancariaEmpresaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.TESORERIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONCILIAR,
        "update": Acciones.CONCILIAR,
        "partial_update": Acciones.CONCILIAR,
        "destroy": Acciones.CONCILIAR,
    }


class MovimientoBancarioViewSet(TenantViewSetMixin, ModelViewSet):
    model = MovimientoBancario
    serializer_class = MovimientoBancarioSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.TESORERIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONCILIAR,
        "update": Acciones.CONCILIAR,
        "partial_update": Acciones.CONCILIAR,
        "destroy": Acciones.CONCILIAR,
        "conciliar": Acciones.CONCILIAR,
        "desconciliar": Acciones.CONCILIAR,
        "bulk_import": Acciones.CONCILIAR,
        "bulk_template": Acciones.VER,
    }

    def perform_create(self, serializer):
        self._set_tenant_context()
        movimiento = TesoreriaBancariaService.registrar_movimiento_manual(
            cuenta_bancaria=serializer.validated_data["cuenta_bancaria"],
            fecha=serializer.validated_data["fecha"],
            referencia=serializer.validated_data.get("referencia", ""),
            descripcion=serializer.validated_data.get("descripcion", ""),
            tipo=serializer.validated_data["tipo"],
            monto=serializer.validated_data["monto"],
            usuario=self.request.user,
        )
        serializer.instance = movimiento

    @action(detail=True, methods=["post"])
    def conciliar(self, request, pk=None):
        self._set_tenant_context()
        movimiento = self.get_object()
        serializer = ConciliarMovimientoBancarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cuenta_por_cobrar = None
        cuenta_por_pagar = None
        if serializer.validated_data.get("cuenta_por_cobrar"):
            cuenta_por_cobrar = CuentaPorCobrar.all_objects.filter(
                empresa=self.get_empresa(),
                id=serializer.validated_data["cuenta_por_cobrar"],
            ).first()
            if not cuenta_por_cobrar:
                raise ResourceNotFoundError("Cuenta por cobrar no encontrada.")

        if serializer.validated_data.get("cuenta_por_pagar"):
            cuenta_por_pagar = CuentaPorPagar.all_objects.filter(
                empresa=self.get_empresa(),
                id=serializer.validated_data["cuenta_por_pagar"],
            ).first()
            if not cuenta_por_pagar:
                raise ResourceNotFoundError("Cuenta por pagar no encontrada.")

        movimiento = TesoreriaBancariaService.conciliar_movimiento(
            movimiento=movimiento,
            cuenta_por_cobrar=cuenta_por_cobrar,
            cuenta_por_pagar=cuenta_por_pagar,
            usuario=request.user,
        )
        return Response(self.get_serializer(movimiento).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def desconciliar(self, request, pk=None):
        self._set_tenant_context()
        movimiento = self.get_object()
        movimiento = TesoreriaBancariaService.desconciliar_movimiento(
            movimiento=movimiento,
            usuario=request.user,
        )
        return Response(self.get_serializer(movimiento).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        self._set_tenant_context()
        payload = import_movimientos_bancarios(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        self._set_tenant_context()
        content = build_movimientos_bancarios_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_movimientos_bancarios.xlsx"'
        return response


class CuentaPorCobrarViewSet(TenantViewSetMixin, ModelViewSet):
    model = CuentaPorCobrar
    serializer_class = CuentaPorCobrarSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.TESORERIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.COBRAR,
        "update": Acciones.COBRAR,
        "partial_update": Acciones.COBRAR,
        "destroy": Acciones.COBRAR,
        "aplicar_pago": Acciones.COBRAR,
        "aging": Acciones.VER,
    }

    @action(detail=True, methods=["post"])
    def aplicar_pago(self, request, pk=None):
        self._set_tenant_context()
        cuenta = self.get_object()
        serializer = AplicarPagoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cuenta = CarteraService.aplicar_pago_cuenta(
            cuenta=cuenta,
            monto=serializer.validated_data["monto"],
            fecha_pago=serializer.validated_data["fecha_pago"],
        )
        return Response(self.get_serializer(cuenta).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def aging(self, request):
        self._set_tenant_context()
        fecha_corte_raw = request.query_params.get("fecha_corte")
        fecha_corte = parse_date(fecha_corte_raw) if fecha_corte_raw else None
        if fecha_corte_raw and fecha_corte is None:
            raise BusinessRuleError(
                "fecha_corte debe tener formato YYYY-MM-DD.",
                error_code="VALIDATION_ERROR",
            )
        fecha_corte = fecha_corte or timezone.localdate()

        cuentas = CuentaPorCobrar.all_objects.filter(empresa=self.get_empresa()).exclude(estado="ANULADA")
        buckets = {"al_dia": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "91_plus": Decimal("0")}
        detalle = []
        for cuenta in cuentas:
            saldo = Decimal(cuenta.saldo or 0)
            if saldo <= 0:
                continue
            dias_vencimiento = (fecha_corte - cuenta.fecha_vencimiento).days
            bucket = _aging_bucket_label(dias_vencimiento)
            buckets[bucket] += saldo
            detalle.append(
                {
                    "id": str(cuenta.id),
                    "referencia": cuenta.referencia,
                    "cliente_id": str(cuenta.cliente_id),
                    "fecha_vencimiento": cuenta.fecha_vencimiento,
                    "dias_vencimiento": dias_vencimiento,
                    "saldo": saldo,
                    "bucket": bucket,
                    "estado": cuenta.estado,
                }
            )
        return Response(
            {"fecha_corte": fecha_corte, "totales": {**buckets, "total": sum(buckets.values(), Decimal("0"))}, "detalle": detalle},
            status=status.HTTP_200_OK,
        )


class CuentaPorPagarViewSet(TenantViewSetMixin, ModelViewSet):
    model = CuentaPorPagar
    serializer_class = CuentaPorPagarSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.TESORERIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.PAGAR,
        "update": Acciones.PAGAR,
        "partial_update": Acciones.PAGAR,
        "destroy": Acciones.PAGAR,
        "aplicar_pago": Acciones.PAGAR,
        "aging": Acciones.VER,
    }

    @action(detail=True, methods=["post"])
    def aplicar_pago(self, request, pk=None):
        self._set_tenant_context()
        cuenta = self.get_object()
        serializer = AplicarPagoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cuenta = CarteraService.aplicar_pago_cuenta(
            cuenta=cuenta,
            monto=serializer.validated_data["monto"],
            fecha_pago=serializer.validated_data["fecha_pago"],
        )
        return Response(self.get_serializer(cuenta).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def aging(self, request):
        self._set_tenant_context()
        fecha_corte_raw = request.query_params.get("fecha_corte")
        fecha_corte = parse_date(fecha_corte_raw) if fecha_corte_raw else None
        if fecha_corte_raw and fecha_corte is None:
            raise BusinessRuleError(
                "fecha_corte debe tener formato YYYY-MM-DD.",
                error_code="VALIDATION_ERROR",
            )
        fecha_corte = fecha_corte or timezone.localdate()

        cuentas = CuentaPorPagar.all_objects.filter(empresa=self.get_empresa()).exclude(estado="ANULADA")
        buckets = {"al_dia": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "91_plus": Decimal("0")}
        detalle = []
        for cuenta in cuentas:
            saldo = Decimal(cuenta.saldo or 0)
            if saldo <= 0:
                continue
            dias_vencimiento = (fecha_corte - cuenta.fecha_vencimiento).days
            bucket = _aging_bucket_label(dias_vencimiento)
            buckets[bucket] += saldo
            detalle.append(
                {
                    "id": str(cuenta.id),
                    "referencia": cuenta.referencia,
                    "proveedor_id": str(cuenta.proveedor_id),
                    "fecha_vencimiento": cuenta.fecha_vencimiento,
                    "dias_vencimiento": dias_vencimiento,
                    "saldo": saldo,
                    "bucket": bucket,
                    "estado": cuenta.estado,
                }
            )
        return Response(
            {"fecha_corte": fecha_corte, "totales": {**buckets, "total": sum(buckets.values(), Decimal("0"))}, "detalle": detalle},
            status=status.HTTP_200_OK,
        )
