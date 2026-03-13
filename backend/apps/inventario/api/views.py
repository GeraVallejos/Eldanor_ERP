from datetime import datetime, time

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
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
from apps.inventario.models import Bodega, InventorySnapshot, MovimientoInventario, ReservaStock, StockProducto
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Producto


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
        "resumen": Acciones.VER,
    }

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        queryset = self.get_queryset().filter(producto__activo=True)
        empresa = self.get_empresa()
        reservas_qs = ReservaStock.all_objects.filter(empresa=empresa, producto__activo=True)

        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        group_by = request.query_params.get("group_by")

        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
            reservas_qs = reservas_qs.filter(producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
            reservas_qs = reservas_qs.filter(bodega_id=bodega_id)

        total_stock = queryset.aggregate(total=Sum("stock"))["total"] or 0
        total_valor = queryset.aggregate(total=Sum("valor_stock"))["total"] or 0
        total_reservado = reservas_qs.aggregate(total=Sum("cantidad"))["total"] or 0
        total_disponible = total_stock - total_reservado

        if group_by == "producto":
            product_qs = Producto.all_objects.filter(empresa=empresa, activo=True)
            if producto_id:
                product_qs = product_qs.filter(id=producto_id)

            stock_filter = Q(stocks__empresa=empresa)
            if bodega_id:
                stock_filter &= Q(stocks__bodega_id=bodega_id)

            detalle = list(
                product_qs.values("id", "nombre", "categoria__nombre")
                .annotate(
                    stock_total=Coalesce(
                        Sum("stocks__stock", filter=stock_filter),
                        Value(0),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    ),
                    valor_total=Coalesce(
                        Sum("stocks__valor_stock", filter=stock_filter),
                        Value(0),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    ),
                )
                .order_by("nombre")
            )
            reservas_por_producto = {
                str(item["producto_id"]): item["reservado_total"]
                for item in reservas_qs.values("producto_id").annotate(
                    reservado_total=Coalesce(
                        Sum("cantidad"),
                        Value(0),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                )
            }

            detalle = [
                {
                    "producto_id": item["id"],
                    "producto__nombre": item["nombre"],
                    "producto__categoria__nombre": item.get("categoria__nombre") or "-",
                    "stock_total": item["stock_total"],
                    "reservado_total": reservas_por_producto.get(str(item["id"]), 0),
                    "disponible_total": item["stock_total"] - reservas_por_producto.get(str(item["id"]), 0),
                    "valor_total": item["valor_total"],
                }
                for item in detalle
            ]
        elif group_by == "bodega":
            reservas_por_bodega = {
                str(item["bodega_id"]): item["reservado_total"]
                for item in reservas_qs.values("bodega_id").annotate(
                    reservado_total=Coalesce(
                        Sum("cantidad"),
                        Value(0),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                )
            }
            detalle = [
                {
                    **item,
                    "reservado_total": reservas_por_bodega.get(str(item["bodega_id"]), 0),
                    "disponible_total": item["stock_total"] - reservas_por_bodega.get(str(item["bodega_id"]), 0),
                }
                for item in list(
                queryset.values("bodega_id", "bodega__nombre")
                .annotate(stock_total=Sum("stock"), valor_total=Sum("valor_stock"))
                .order_by("bodega__nombre")
                )
            ]
        else:
            detalle = []

        return Response(
            {
                "totales": {
                    "stock_total": total_stock,
                    "reservado_total": total_reservado,
                    "disponible_total": total_disponible,
                    "valor_total": total_valor,
                },
                "group_by": group_by,
                "detalle": detalle,
            },
            status=status.HTTP_200_OK,
        )


class KardexPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


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

    @staticmethod
    def _parse_instant(value, *, end_of_day=False):
        if not value:
            return None
        dt = parse_datetime(value)
        if dt is not None:
            return dt
        d = parse_date(value)
        if d is None:
            return None
        return datetime.combine(d, time.max if end_of_day else time.min)

    @action(detail=False, methods=["get"])
    def kardex(self, request):
        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        desde = self._parse_instant(request.query_params.get("desde"))
        hasta = self._parse_instant(request.query_params.get("hasta"), end_of_day=True)
        tipo = request.query_params.get("tipo")
        documento_tipo = request.query_params.get("documento_tipo")
        referencia = request.query_params.get("referencia")
        if not producto_id:
            return Response({"detail": "producto_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        movimientos = InventarioService.obtener_kardex(
            empresa=request.user.empresa_activa,
            producto_id=producto_id,
            bodega_id=bodega_id,
            desde=desde,
            hasta=hasta,
            tipo=tipo,
            documento_tipo=documento_tipo,
            referencia=referencia,
        )

        paginator = KardexPagination()
        page = paginator.paginate_queryset(movimientos, request)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

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
