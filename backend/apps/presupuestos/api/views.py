from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from apps.core.mixins import TenantViewSetMixin
from apps.presupuestos.models import Presupuesto
from apps.presupuestos.services.presupuesto_service import PresupuestoService
from apps.presupuestos.api.serializer import PresupuestoSerializer
from apps.core.permisos.permissions import TieneRelacionActiva
from rest_framework.permissions import IsAuthenticated


class PresupuestoViewSet(TenantViewSetMixin, ModelViewSet):
    serializer_class = PresupuestoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva]
    queryset = Presupuesto.objects.all()  

    def destroy(self, request, *args, **kwargs):
        # self.get_object() ya verifica que pertenezca a la empresa por el Mixin
        presupuesto = self.get_object()

        # Llamada corregida al Service
        PresupuestoService.eliminar_presupuesto(
            presupuesto_id=presupuesto.id, # <--- Pasar el ID
            empresa=request.user.empresa,  # <--- Faltaba este argumento
            usuario=request.user
        )
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        presupuesto = self.get_object()

        PresupuestoService.anular_presupuesto(
            presupuesto_id=presupuesto.id, # <--- Pasar el ID
            empresa=request.user.empresa,  # <--- Faltaba este argumento
            usuario=request.user
        )
        return Response({"detail": "Presupuesto anulado correctamente."})

    @action(detail=True, methods=["post"])
    def aprobar(self, request, pk=None):
        # Aquí ya lo tenías casi bien, pk es el ID que viene en la URL
        presupuesto = PresupuestoService.aprobar_presupuesto(
            presupuesto_id=pk,
            empresa=request.user.empresa,
            usuario=request.user
        )
        return Response({"status": "Presupuesto aprobado"})