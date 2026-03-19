from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.contabilidad.api.serializers import AsientoContableSerializer, MovimientoContableSerializer, PlanCuentaSerializer
from apps.contabilidad.models import AsientoContable, MovimientoContable, PlanCuenta
from apps.contabilidad.services import ContabilidadService
from apps.core.exceptions import ResourceNotFoundError
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva


class PlanCuentaViewSet(TenantViewSetMixin, ModelViewSet):
    model = PlanCuenta
    serializer_class = PlanCuentaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTABILIDAD
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONTABILIZAR,
        "update": Acciones.CONTABILIZAR,
        "partial_update": Acciones.CONTABILIZAR,
        "destroy": Acciones.CONTABILIZAR,
        "seed_base": Acciones.CONTABILIZAR,
    }

    @action(detail=False, methods=["post"])
    def seed_base(self, request):
        self._set_tenant_context()
        creadas = ContabilidadService.seed_plan_base(
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response({"created": len(creadas)}, status=status.HTTP_200_OK)


class AsientoContableViewSet(TenantViewSetMixin, ModelViewSet):
    model = AsientoContable
    serializer_class = AsientoContableSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTABILIDAD
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONTABILIZAR,
        "update": Acciones.CONTABILIZAR,
        "partial_update": Acciones.CONTABILIZAR,
        "destroy": Acciones.CONTABILIZAR,
        "contabilizar": Acciones.CONTABILIZAR,
        "anular": Acciones.CONTABILIZAR,
        "procesar_solicitudes": Acciones.CONTABILIZAR,
    }

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cuentas = {
            str(cuenta.id): cuenta
            for cuenta in PlanCuenta.all_objects.filter(
                empresa=self.get_empresa(),
                id__in=[item["cuenta"] for item in serializer.validated_data["movimientos_data"]],
            )
        }

        movimientos_data = []
        for item in serializer.validated_data["movimientos_data"]:
            cuenta = cuentas.get(str(item["cuenta"]))
            if not cuenta:
                raise ResourceNotFoundError("Cuenta contable no encontrada.")
            movimientos_data.append(
                {
                    "cuenta": cuenta,
                    "glosa": item.get("glosa") or serializer.validated_data["glosa"],
                    "debe": item.get("debe", 0),
                    "haber": item.get("haber", 0),
                }
            )

        asiento = ContabilidadService.crear_asiento(
            empresa=self.get_empresa(),
            fecha=serializer.validated_data["fecha"],
            glosa=serializer.validated_data["glosa"],
            movimientos_data=movimientos_data,
            usuario=request.user,
            referencia_tipo=serializer.validated_data.get("referencia_tipo", ""),
            referencia_id=serializer.validated_data.get("referencia_id"),
        )
        return Response(self.get_serializer(asiento).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def contabilizar(self, request, pk=None):
        self._set_tenant_context()
        asiento = ContabilidadService.contabilizar_asiento(
            asiento_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(self.get_serializer(asiento).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        self._set_tenant_context()
        asiento = ContabilidadService.anular_asiento(
            asiento_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(self.get_serializer(asiento).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def procesar_solicitudes(self, request):
        self._set_tenant_context()
        procesados = ContabilidadService.procesar_solicitudes_pendientes(
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response({"processed": len(procesados)}, status=status.HTTP_200_OK)


class MovimientoContableViewSet(TenantViewSetMixin, ModelViewSet):
    model = MovimientoContable
    serializer_class = MovimientoContableSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTABILIDAD
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CONTABILIZAR,
        "update": Acciones.CONTABILIZAR,
        "partial_update": Acciones.CONTABILIZAR,
        "destroy": Acciones.CONTABILIZAR,
    }
