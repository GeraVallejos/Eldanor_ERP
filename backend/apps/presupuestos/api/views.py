from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from apps.core.mixins import TenantViewSetMixin
from apps.presupuestos.models import Presupuesto, PresupuestoItem
from apps.presupuestos.services.presupuesto_service import PresupuestoService
from apps.presupuestos.api.serializer import PresupuestoSerializer
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from apps.presupuestos.api.serializer import PresupuestoItemSerializer
from rest_framework.permissions import IsAuthenticated


class PresupuestoViewSet(TenantViewSetMixin, ModelViewSet):
    serializer_class = PresupuestoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    queryset = Presupuesto.objects.all()  
    permission_modulo = Modulos.PRESUPUESTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "aprobar": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        presupuesto = PresupuestoService.crear_presupuesto(
            data=serializer.validated_data,
            empresa=request.user.empresa_activa,
            usuario=request.user,
        )

        output_serializer = self.get_serializer(presupuesto)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        # self.get_object() ya verifica que pertenezca a la empresa por el Mixin
        presupuesto = self.get_object()

        # Llamada corregida al Service
        PresupuestoService.eliminar_presupuesto(
            presupuesto_id=presupuesto.id, 
            empresa=request.user.empresa_activa,  
            usuario=request.user
        )
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        presupuesto = self.get_object()

        PresupuestoService.anular_presupuesto(
            presupuesto_id=presupuesto.id, 
            empresa=request.user.empresa_activa,  
            usuario=request.user
        )
        return Response({"detail": "Presupuesto anulado correctamente."})

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        presupuesto = self.get_object()
        presupuesto = PresupuestoService.aprobar_presupuesto(
            presupuesto_id=presupuesto.id,
            empresa=request.user.empresa_activa,
            usuario=request.user
        )
        return Response({"status": "Presupuesto aprobado"})
    

class PresupuestoItemViewSet(TenantViewSetMixin, ModelViewSet):
    queryset = PresupuestoItem.objects.all()
    serializer_class = PresupuestoItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRESUPUESTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }
