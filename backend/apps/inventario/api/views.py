from datetime import datetime, time

from django.db.models import Count, DecimalField, Q, Sum, Value
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
    PrevisualizacionRegularizacionSerializer,
    RegularizacionInventarioSerializer,
    StockProductoSerializer,
    TrasladoInventarioSerializer,
)
from apps.inventario.models import Bodega, InventorySnapshot, MovimientoInventario, ReservaStock, StockProducto
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Producto


class BodegaViewSet(TenantViewSetMixin, ModelViewSet):
    model = Bodega
    serializer_class = BodegaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
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
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "resumen": Acciones.VER,
        "criticos": Acciones.VER,
        "analytics": Acciones.VER,
    }

    def _build_resumen_payload(self, request, *, include_filters=False):
        """Construye el payload valorizado de inventario para resumen y reportes."""
        queryset = self.get_queryset().filter(producto__activo=True)
        empresa = self.get_empresa()
        reservas_qs = ReservaStock.all_objects.filter(empresa=empresa, producto__activo=True)

        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        group_by = request.query_params.get("group_by")
        only_with_stock = str(request.query_params.get("only_with_stock", "")).lower() in {
            "1",
            "true",
            "si",
        }

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

        if only_with_stock:
            detalle = [item for item in detalle if (item.get("stock_total") or 0) > 0]

        payload = {
            "totales": {
                "stock_total": total_stock,
                "reservado_total": total_reservado,
                "disponible_total": total_disponible,
                "valor_total": total_valor,
            },
            "group_by": group_by,
            "detalle": detalle,
        }
        if include_filters:
            payload["filters"] = {
                "producto_id": producto_id or "",
                "bodega_id": bodega_id or "",
                "group_by": group_by or "",
                "only_with_stock": only_with_stock,
            }
        return payload

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        return Response(self._build_resumen_payload(request), status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """Entrega el reporte analitico valorizado de inventario listo para frontend."""
        payload = self._build_resumen_payload(request, include_filters=True)
        detalle = payload["detalle"]
        top_valorizados = sorted(
            detalle,
            key=lambda item: (item.get("valor_total") or 0, item.get("stock_total") or 0),
            reverse=True,
        )[:5]
        criticos_qs = self.get_queryset().filter(
            producto__activo=True,
            producto__maneja_inventario=True,
            producto__stock_minimo__gt=0,
        )
        if request.query_params.get("bodega_id"):
            criticos_qs = criticos_qs.filter(bodega_id=request.query_params.get("bodega_id"))
        criticos = list(
            criticos_qs.values(
                "producto_id",
                "producto__nombre",
                "producto__sku",
                "producto__stock_minimo",
            )
            .annotate(
                stock_total=Coalesce(
                    Sum("stock"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
            .order_by("producto__nombre")
        )
        payload["top_valorizados"] = top_valorizados
        payload["criticos"] = [
            {
                **item,
                "faltante": max(
                    (item["producto__stock_minimo"] or 0) - (item["stock_total"] or 0),
                    0,
                ),
            }
            for item in criticos
            if (item["stock_total"] or 0) <= (item["producto__stock_minimo"] or 0)
        ]
        payload["metrics"] = {
            "registros": len(detalle),
            "con_stock": sum(1 for item in detalle if (item.get("stock_total") or 0) > 0),
            "valor_total": payload["totales"]["valor_total"],
            "stock_total": payload["totales"]["stock_total"],
        }
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def criticos(self, request):
        queryset = self.get_queryset().filter(
            producto__activo=True,
            producto__maneja_inventario=True,
            producto__stock_minimo__gt=0,
        )

        bodega_id = request.query_params.get("bodega_id")
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)

        detalle = list(
            queryset.values(
                "producto_id",
                "producto__nombre",
                "producto__sku",
                "producto__stock_minimo",
            )
            .annotate(
                stock_total=Coalesce(
                    Sum("stock"),
                    Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                valor_total=Coalesce(
                    Sum("valor_stock"),
                    Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
            )
            .order_by("producto__nombre")
        )

        criticos = [
            {
                **item,
                "faltante": max(
                    (item["producto__stock_minimo"] or 0) - (item["stock_total"] or 0),
                    0,
                ),
            }
            for item in detalle
            if (item["stock_total"] or 0) <= (item["producto__stock_minimo"] or 0)
        ]

        return Response(
            {
                "count": len(criticos),
                "detalle": criticos,
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
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "kardex": Acciones.VER,
        "snapshot": Acciones.VER,
        "resumen_operativo": Acciones.VER,
        "previsualizar_regularizacion": Acciones.EDITAR,
        "regularizar": Acciones.EDITAR,
        "trasladar": Acciones.EDITAR,
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
        documento_tipos = [valor.strip() for valor in str(documento_tipo or "").split(",") if valor.strip()]
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
            documento_tipo=documento_tipos,
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

    @action(detail=False, methods=["get"])
    def resumen_operativo(self, request):
        empresa = request.user.empresa_activa
        queryset = self.get_queryset()

        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        desde = self._parse_instant(request.query_params.get("desde"))
        hasta = self._parse_instant(request.query_params.get("hasta"), end_of_day=True)

        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        if desde is not None:
            queryset = queryset.filter(creado_en__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(creado_en__lte=hasta)

        agregados = queryset.aggregate(
            total_movimientos=Count("id"),
            entradas=Count("id", filter=Q(tipo="ENTRADA")),
            salidas=Count("id", filter=Q(tipo="SALIDA")),
            ajustes=Count("id", filter=Q(documento_tipo="AJUSTE")),
            traslados=Count("id", filter=Q(documento_tipo="TRASLADO")),
            cantidad_entrada=Coalesce(
                Sum("cantidad", filter=Q(tipo="ENTRADA")),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            cantidad_salida=Coalesce(
                Sum("cantidad", filter=Q(tipo="SALIDA")),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )

        cantidad_entrada = agregados["cantidad_entrada"] or 0
        cantidad_salida = agregados["cantidad_salida"] or 0

        return Response(
            {
                "empresa_id": str(empresa.id),
                "total_movimientos": agregados["total_movimientos"] or 0,
                "entradas": agregados["entradas"] or 0,
                "salidas": agregados["salidas"] or 0,
                "ajustes": agregados["ajustes"] or 0,
                "traslados": agregados["traslados"] or 0,
                "cantidad_entrada": cantidad_entrada,
                "cantidad_salida": cantidad_salida,
                "neto_unidades": cantidad_entrada - cantidad_salida,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def previsualizar_regularizacion(self, request):
        serializer = PrevisualizacionRegularizacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = InventarioService.previsualizar_regularizacion_stock(
            producto_id=serializer.validated_data["producto_id"],
            bodega_id=serializer.validated_data.get("bodega_id"),
            stock_objetivo=serializer.validated_data["stock_objetivo"],
            empresa=request.user.empresa_activa,
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def regularizar(self, request):
        serializer = RegularizacionInventarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        movimiento = InventarioService.regularizar_stock(
            producto_id=serializer.validated_data["producto_id"],
            bodega_id=serializer.validated_data.get("bodega_id"),
            stock_objetivo=serializer.validated_data["stock_objetivo"],
            referencia=serializer.validated_data["referencia"],
            empresa=request.user.empresa_activa,
            usuario=request.user,
            costo_unitario=serializer.validated_data.get("costo_unitario"),
            lote_codigo=serializer.validated_data.get("lote_codigo", ""),
            fecha_vencimiento=serializer.validated_data.get("fecha_vencimiento"),
            series=serializer.validated_data.get("series"),
        )
        return Response(
            MovimientoInventarioSerializer(movimiento).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def trasladar(self, request):
        serializer = TrasladoInventarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        traslado = InventarioService.trasladar_stock(
            producto_id=serializer.validated_data["producto_id"],
            bodega_origen_id=serializer.validated_data["bodega_origen_id"],
            bodega_destino_id=serializer.validated_data["bodega_destino_id"],
            cantidad=serializer.validated_data["cantidad"],
            referencia=serializer.validated_data["referencia"],
            empresa=request.user.empresa_activa,
            usuario=request.user,
            lote_codigo=serializer.validated_data.get("lote_codigo", ""),
        )
        return Response(
            {
                "traslado_id": traslado["traslado_id"],
                "movimiento_salida": MovimientoInventarioSerializer(traslado["movimiento_salida"]).data,
                "movimiento_entrada": MovimientoInventarioSerializer(traslado["movimiento_entrada"]).data,
            },
            status=status.HTTP_201_CREATED,
        )


class InventorySnapshotViewSet(TenantViewSetMixin, ModelViewSet):
    model = InventorySnapshot
    serializer_class = InventorySnapshotSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
    }
