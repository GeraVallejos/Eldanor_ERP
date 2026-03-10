from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.compras.api.serializer import (
    OrdenCompraItemSerializer,
    OrdenCompraSerializer,
    RecepcionCompraItemSerializer,
    RecepcionCompraSerializer,
)
from apps.compras.models import OrdenCompra, OrdenCompraItem, RecepcionCompra, RecepcionCompraItem
from apps.compras.services import OrdenCompraService, RecepcionCompraService
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva


class OrdenCompraViewSet(TenantViewSetMixin, ModelViewSet):
    model = OrdenCompra
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "enviar": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
    }

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


class RecepcionCompraViewSet(TenantViewSetMixin, ModelViewSet):
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

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        recepcion = RecepcionCompraService.confirmar_recepcion(
            recepcion_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
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
