from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.inventario.api.serializer import (
    BodegaSerializer,
    InventorySnapshotSerializer,
    MovimientoInventarioSerializer,
    StockProductoSerializer,
)
from apps.inventario.models import Bodega, InventorySnapshot, MovimientoInventario, StockProducto
from apps.inventario.services.inventario_service import InventarioService


class BodegaViewSet(TenantViewSetMixin, ModelViewSet):
    model = Bodega
    serializer_class = BodegaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class StockProductoViewSet(TenantViewSetMixin, ModelViewSet):
    model = StockProducto
    serializer_class = StockProductoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class MovimientoInventarioViewSet(TenantViewSetMixin, ModelViewSet):
    model = MovimientoInventario
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "kardex": Acciones.VER,
        "snapshot": Acciones.VER,
    }

    @action(detail=False, methods=["get"])
    def kardex(self, request):
        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        if not producto_id:
            return Response({"detail": "producto_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        movimientos = InventarioService.obtener_kardex(
            empresa=request.user.empresa_activa,
            producto_id=producto_id,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(movimientos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def snapshot(self, request):
        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        hasta_raw = request.query_params.get("hasta")
        if not producto_id or not bodega_id:
            return Response(
                {"detail": "producto_id y bodega_id son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hasta = parse_datetime(hasta_raw) if hasta_raw else None
        snap = InventarioService.obtener_snapshot(
            empresa=request.user.empresa_activa,
            producto_id=producto_id,
            bodega_id=bodega_id,
            hasta=hasta,
        )
        if not snap:
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = InventorySnapshotSerializer(snap)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InventorySnapshotViewSet(TenantViewSetMixin, ModelViewSet):
    model = InventorySnapshot
    serializer_class = InventorySnapshotSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
    }
