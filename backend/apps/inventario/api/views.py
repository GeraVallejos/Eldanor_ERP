from datetime import datetime, time

from django.http import HttpResponse
from django.db.models import Count, DecimalField, Exists, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.auditoria.api.serializer import AuditEventSerializer
from apps.auditoria.models import AuditEvent
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.inventario.api.serializer import (
    AjusteInventarioMasivoCreateSerializer,
    AjusteInventarioMasivoSerializer,
    AjusteInventarioMasivoUpdateSerializer,
    AnularLoteSerializer,
    BodegaSerializer,
    CorteInventarioCreateSerializer,
    CorteInventarioCierreMensualSerializer,
    CorteInventarioItemSerializer,
    CorteInventarioSerializer,
    CorregirLoteSerializer,
    InventorySnapshotSerializer,
    MovimientoInventarioSerializer,
    PrevisualizacionRegularizacionSerializer,
    RegularizacionInventarioSerializer,
    StockLoteSerializer,
    StockProductoSerializer,
    TrasladoInventarioMasivoCreateSerializer,
    TrasladoInventarioMasivoSerializer,
    TrasladoInventarioMasivoUpdateSerializer,
    TrasladoInventarioSerializer,
)
from apps.inventario.models import (
    AjusteInventarioMasivo,
    Bodega,
    CorteInventario,
    EstadoDocumentoInventario,
    InventorySnapshot,
    MovimientoInventario,
    ReservaStock,
    StockLote,
    StockProducto,
    StockSerie,
    TrasladoInventarioMasivo,
)
from apps.inventario.services.bulk_import_service import (
    build_ajustes_masivos_bulk_template,
    build_traslados_masivos_bulk_template,
    import_ajustes_masivos_desde_archivo,
    import_traslados_masivos_desde_archivo,
)
from apps.inventario.services.corte_inventario_service import CorteInventarioService
from apps.inventario.services.documento_inventario_service import DocumentoInventarioService
from apps.inventario.services.bodega_service import BodegaService
from apps.inventario.services.inventario_service import InventarioService
from apps.inventario.services.lote_service import LoteService
from apps.productos.models import Producto


def _parse_inventario_instant(value, *, end_of_day=False):
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is not None:
        return dt
    d = parse_date(value)
    if d is None:
        return None
    return datetime.combine(d, time.max if end_of_day else time.min)


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

    def get_queryset(self):
        queryset = super().get_queryset()
        empresa = self.get_empresa()
        return queryset.annotate(
            has_movimientos=Exists(
                MovimientoInventario.all_objects.filter(empresa=empresa, bodega_id=OuterRef("pk"))
            ),
            has_stocks=Exists(
                StockProducto.all_objects.filter(empresa=empresa, bodega_id=OuterRef("pk"))
            ),
            has_snapshots=Exists(
                InventorySnapshot.all_objects.filter(empresa=empresa, bodega_id=OuterRef("pk"))
            ),
            has_reservas=Exists(
                ReservaStock.all_objects.filter(empresa=empresa, bodega_id=OuterRef("pk"))
            ),
            has_stocks_lote=Exists(
                StockLote.all_objects.filter(empresa=empresa, bodega_id=OuterRef("pk"))
            ),
            has_series=Exists(
                StockSerie.all_objects.filter(empresa=empresa, bodega_id=OuterRef("pk"))
            ),
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bodega = BodegaService.crear_bodega(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        output = self.get_serializer(bodega)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        bodega = BodegaService.actualizar_bodega(
            bodega_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        output = self.get_serializer(bodega)
        return Response(output.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        result = BodegaService.eliminar_bodega(
            bodega_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        if result["deleted"]:
            return Response(status=status.HTTP_204_NO_CONTENT)

        output = self.get_serializer(result["bodega"])
        return Response({"deleted": False, "bodega": output.data}, status=status.HTTP_200_OK)


class StockProductoViewSet(TenantViewSetMixin, ReadOnlyModelViewSet):
    model = StockProducto
    serializer_class = StockProductoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "resumen": Acciones.VER,
        "criticos": Acciones.VER,
        "analytics": Acciones.VER,
        "reconciliation": Acciones.VER,
    }

    def _build_stock_base_queryset(self, request):
        """Construye el queryset base de stock con filtros operativos compartidos."""
        queryset = self.get_queryset().filter(producto__activo=True)
        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        return queryset

    def _build_stock_with_snapshot_queryset(self, request):
        """Anota stock actual con ultimo snapshot para conciliacion y salud."""
        latest_snapshot_qs = InventorySnapshot.all_objects.filter(
            empresa=self.get_empresa(),
            producto_id=OuterRef("producto_id"),
            bodega_id=OuterRef("bodega_id"),
        ).order_by("-creado_en", "-id")
        return self._build_stock_base_queryset(request).annotate(
            latest_snapshot_stock=Subquery(latest_snapshot_qs.values("stock")[:1]),
            latest_snapshot_valor=Subquery(latest_snapshot_qs.values("valor_stock")[:1]),
            latest_snapshot_at=Subquery(latest_snapshot_qs.values("creado_en")[:1]),
            producto_nombre=F("producto__nombre"),
            bodega_nombre=F("bodega__nombre"),
        )

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
            producto_ids = [item["producto_id"] for item in detalle]
            lotes_qs = StockLote.all_objects.filter(
                empresa=empresa,
                producto_id__in=producto_ids,
                stock__gt=0,
            )
            if bodega_id:
                lotes_qs = lotes_qs.filter(bodega_id=bodega_id)

            series_qs = StockSerie.all_objects.filter(
                empresa=empresa,
                producto_id__in=producto_ids,
                estado="DISPONIBLE",
            )
            if bodega_id:
                series_qs = series_qs.filter(bodega_id=bodega_id)

            lotes_por_producto = {}
            for lote in lotes_qs.values("producto_id", "lote_codigo", "fecha_vencimiento").order_by("lote_codigo"):
                bucket = lotes_por_producto.setdefault(str(lote["producto_id"]), {"codes": [], "next_expiry": None})
                codigo = lote["lote_codigo"] or ""
                if codigo and codigo not in bucket["codes"]:
                    bucket["codes"].append(codigo)
                vencimiento = lote.get("fecha_vencimiento")
                if vencimiento is not None and (bucket["next_expiry"] is None or vencimiento < bucket["next_expiry"]):
                    bucket["next_expiry"] = vencimiento

            series_por_producto = {}
            for serie in series_qs.values("producto_id", "serie_codigo").order_by("serie_codigo"):
                bucket = series_por_producto.setdefault(str(serie["producto_id"]), {"count": 0, "sample": []})
                bucket["count"] += 1
                if serie["serie_codigo"] and len(bucket["sample"]) < 3:
                    bucket["sample"].append(serie["serie_codigo"])

            for item in detalle:
                lotes_info = lotes_por_producto.get(str(item["producto_id"]), {})
                series_info = series_por_producto.get(str(item["producto_id"]), {})
                item["lotes_activos"] = ", ".join(lotes_info.get("codes", [])) or "-"
                item["proximo_vencimiento"] = (
                    lotes_info.get("next_expiry").isoformat()
                    if lotes_info.get("next_expiry") is not None
                    else None
                )
                item["series_disponibles"] = series_info.get("count", 0)
                item["series_muestra"] = ", ".join(series_info.get("sample", [])) or "-"
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

        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        stock_with_snapshot = self._build_stock_with_snapshot_queryset(request)
        reconciliation_qs = stock_with_snapshot.exclude(
            latest_snapshot_stock__isnull=True,
        ).exclude(
            Q(stock=F("latest_snapshot_stock")) & Q(valor_stock=F("latest_snapshot_valor")),
        )
        reconciliation_rows = []
        for row in reconciliation_qs.values(
            "producto_id",
            "producto_nombre",
            "bodega_id",
            "bodega_nombre",
            "stock",
            "valor_stock",
            "latest_snapshot_stock",
            "latest_snapshot_valor",
            "latest_snapshot_at",
        ).order_by("producto_nombre", "bodega_nombre")[:20]:
            reconciliation_rows.append(
                {
                    "producto_id": row["producto_id"],
                    "producto_nombre": row["producto_nombre"],
                    "bodega_id": row["bodega_id"],
                    "bodega_nombre": row["bodega_nombre"],
                    "stock_actual": row["stock"] or 0,
                    "stock_snapshot": row["latest_snapshot_stock"] or 0,
                    "valor_actual": row["valor_stock"] or 0,
                    "valor_snapshot": row["latest_snapshot_valor"] or 0,
                    "ultimo_snapshot_en": row["latest_snapshot_at"],
                }
            )

        reservas_qs = ReservaStock.all_objects.filter(
            empresa=self.get_empresa(),
            producto__activo=True,
        )
        if producto_id:
            reservas_qs = reservas_qs.filter(producto_id=producto_id)
        if bodega_id:
            reservas_qs = reservas_qs.filter(bodega_id=bodega_id)

        payload["health"] = {
            "productos_criticos": len(payload["criticos"]),
            "reservas_activas": reservas_qs.count(),
            "unidades_reservadas": reservas_qs.aggregate(total=Sum("cantidad"))["total"] or 0,
            "bodegas_con_stock": self._build_stock_base_queryset(request).filter(stock__gt=0).values("bodega_id").distinct().count(),
            "sin_snapshot": stock_with_snapshot.filter(latest_snapshot_stock__isnull=True).count(),
            "descuadrados_snapshot": reconciliation_qs.count(),
        }
        payload["reconciliation"] = {
            "count": reconciliation_qs.count(),
            "detail": reconciliation_rows,
        }
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def reconciliation(self, request):
        """Entrega conciliacion paginada entre stock actual y ultimo snapshot."""
        queryset = self._build_stock_with_snapshot_queryset(request).exclude(
            latest_snapshot_stock__isnull=True,
        ).exclude(
            Q(stock=F("latest_snapshot_stock")) & Q(valor_stock=F("latest_snapshot_valor")),
        ).order_by("producto_nombre", "bodega_nombre", "id")
        paginator = InventarioReconciliationPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        rows = [
            {
                "producto_id": row.producto_id,
                "producto_nombre": row.producto_nombre,
                "bodega_id": row.bodega_id,
                "bodega_nombre": row.bodega_nombre,
                "stock_actual": row.stock or 0,
                "stock_snapshot": row.latest_snapshot_stock or 0,
                "valor_actual": row.valor_stock or 0,
                "valor_snapshot": row.latest_snapshot_valor or 0,
                "ultimo_snapshot_en": row.latest_snapshot_at,
            }
            for row in page
        ]
        return paginator.get_paginated_response(rows)

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


class StockLoteViewSet(TenantViewSetMixin, ReadOnlyModelViewSet):
    model = StockLote
    serializer_class = StockLoteSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "corregir_codigo": Acciones.EDITAR,
        "anular": Acciones.BORRAR,
    }
    http_method_names = ["get", "post", "head", "options", "delete"]

    def get_queryset(self):
        return LoteService.listar_lotes(
            empresa=self.get_empresa(),
            producto_id=self.request.query_params.get("producto_id"),
            bodega_id=self.request.query_params.get("bodega_id"),
        )

    @action(detail=True, methods=["post"])
    def corregir_codigo(self, request, pk=None):
        serializer = CorregirLoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lote = LoteService.corregir_codigo(
            lote_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
            nuevo_codigo=serializer.validated_data["nuevo_codigo"],
            motivo=serializer.validated_data["motivo"],
        )
        output = self.get_serializer(lote)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        serializer = AnularLoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LoteService.anular_lote(
            lote_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
            motivo=serializer.validated_data["motivo"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class KardexPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class InventarioAuditPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class InventarioReconciliationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class InventarioCorteItemPagination(PageNumberPagination):
    page_size = 25
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
        "historial": Acciones.VER,
        "auditoria": Acciones.VER,
        "resumen_operativo": Acciones.VER,
        "previsualizar_regularizacion": Acciones.EDITAR,
        "regularizar": Acciones.EDITAR,
        "trasladar": Acciones.EDITAR,
    }

    @staticmethod
    def _parse_instant(value, *, end_of_day=False):
        return _parse_inventario_instant(value, end_of_day=end_of_day)

    def _enriquecer_eventos_auditoria(self, eventos):
        movimiento_ids = [
            row.get("entity_id")
            for row in eventos
            if row.get("entity_type") == "MOVIMIENTO_INVENTARIO" and row.get("entity_id")
        ]
        if not movimiento_ids:
            return eventos

        movimientos = list(
            self.get_queryset()
            .filter(id__in=movimiento_ids)
            .values("id", "documento_tipo", "documento_id", "tipo", "bodega_id")
        )
        movimientos_por_id = {str(row["id"]): row for row in movimientos}

        traslado_ids = {
            str(row["documento_id"])
            for row in movimientos
            if row["documento_tipo"] == "TRASLADO" and row["documento_id"]
        }
        traslados_por_documento = {}
        if traslado_ids:
            movimientos_traslado = (
                self.get_queryset()
                .filter(documento_tipo="TRASLADO", documento_id__in=traslado_ids)
                .values("id", "documento_id", "tipo", "bodega_id")
            )
            for row in movimientos_traslado:
                traslados_por_documento.setdefault(str(row["documento_id"]), []).append(row)

        eventos_enriquecidos = []
        for row in eventos:
            payload = row.get("payload")
            if not isinstance(payload, dict):
                eventos_enriquecidos.append(row)
                continue

            movimiento = movimientos_por_id.get(str(row.get("entity_id")))
            if not movimiento or movimiento["documento_tipo"] != "TRASLADO" or not movimiento["documento_id"]:
                eventos_enriquecidos.append(row)
                continue

            origen = None
            destino = None
            relacionados = traslados_por_documento.get(str(movimiento["documento_id"]), [])
            for relacionado in relacionados:
                if relacionado["tipo"] == "SALIDA":
                    origen = relacionado
                elif relacionado["tipo"] == "ENTRADA":
                    destino = relacionado

            payload_enriquecido = dict(payload)
            payload_enriquecido["bodega_origen_id"] = str(origen["bodega_id"]) if origen else None
            payload_enriquecido["bodega_destino_id"] = str(destino["bodega_id"]) if destino else None

            row_enriquecido = dict(row)
            row_enriquecido["payload"] = payload_enriquecido
            eventos_enriquecidos.append(row_enriquecido)

        return eventos_enriquecidos

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
    def historial(self, request):
        empresa = self.get_empresa()
        movimientos_qs = self.get_queryset()

        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        documento_tipo = request.query_params.get("documento_tipo")
        documento_id = request.query_params.get("documento_id")
        tipo = request.query_params.get("tipo")
        referencia = request.query_params.get("referencia")
        desde = self._parse_instant(request.query_params.get("desde"))
        hasta = self._parse_instant(request.query_params.get("hasta"), end_of_day=True)

        if producto_id:
            movimientos_qs = movimientos_qs.filter(producto_id=producto_id)
        if bodega_id:
            movimientos_qs = movimientos_qs.filter(bodega_id=bodega_id)
        if documento_tipo:
            movimientos_qs = movimientos_qs.filter(documento_tipo=documento_tipo)
        if documento_id:
            movimientos_qs = movimientos_qs.filter(documento_id=documento_id)
        if tipo:
            movimientos_qs = movimientos_qs.filter(tipo=tipo)
        if referencia:
            movimientos_qs = movimientos_qs.filter(referencia__icontains=referencia)
        if desde is not None:
            movimientos_qs = movimientos_qs.filter(creado_en__gte=desde)
        if hasta is not None:
            movimientos_qs = movimientos_qs.filter(creado_en__lte=hasta)

        paginator = InventarioAuditPagination()
        page_movimientos = paginator.paginate_queryset(
            movimientos_qs.order_by("-creado_en", "-id"),
            request,
            view=self,
        )
        movimiento_ids = [str(row.id) for row in page_movimientos]
        audit_qs = AuditEvent.all_objects.filter(
            empresa=empresa,
            module_code=Modulos.INVENTARIO,
            entity_type="MOVIMIENTO_INVENTARIO",
            entity_id__in=movimiento_ids,
        ).order_by("-occurred_at", "-id")
        serializer = AuditEventSerializer(audit_qs, many=True)
        return paginator.get_paginated_response(self._enriquecer_eventos_auditoria(list(serializer.data)))

    @action(detail=True, methods=["get"])
    def auditoria(self, request, pk=None):
        movimiento = self.get_object()
        entities = [("MOVIMIENTO_INVENTARIO", movimiento.id)]

        if movimiento.documento_tipo == "TRASLADO" and movimiento.documento_id:
            traslado_ids = (
                self.get_queryset()
                .filter(documento_tipo=movimiento.documento_tipo, documento_id=movimiento.documento_id)
                .values_list("id", flat=True)
            )
            entities.extend(("MOVIMIENTO_INVENTARIO", mov_id) for mov_id in traslado_ids)

        audit_qs = AuditEvent.all_objects.filter(
            empresa=self.get_empresa(),
            module_code=Modulos.INVENTARIO,
            entity_type="MOVIMIENTO_INVENTARIO",
            entity_id__in=[str(entity_id) for entity_type, entity_id in entities if entity_type == "MOVIMIENTO_INVENTARIO"],
        ).order_by("-occurred_at", "-id")
        paginator = InventarioAuditPagination()
        page = paginator.paginate_queryset(audit_qs, request, view=self)
        serializer = AuditEventSerializer(page, many=True)
        return paginator.get_paginated_response(self._enriquecer_eventos_auditoria(list(serializer.data)))

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


class CorteInventarioViewSet(TenantViewSetMixin, ModelViewSet):
    model = CorteInventario
    serializer_class = CorteInventarioSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "cierre_mensual": Acciones.CREAR,
        "items": Acciones.VER,
    }
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        queryset = super().get_queryset().order_by("-fecha_corte", "-creado_en", "-id")
        fecha_corte = self.request.query_params.get("fecha_corte")
        tipo_corte = self.request.query_params.get("tipo_corte")
        periodo_referencia = self.request.query_params.get("periodo_referencia")
        desde = self.request.query_params.get("desde")
        hasta = self.request.query_params.get("hasta")

        if fecha_corte:
            queryset = queryset.filter(fecha_corte=fecha_corte)
        if tipo_corte:
            queryset = queryset.filter(tipo_corte=tipo_corte)
        if periodo_referencia:
            queryset = queryset.filter(periodo_referencia=periodo_referencia)
        if desde:
            queryset = queryset.filter(fecha_corte__gte=desde)
        if hasta:
            queryset = queryset.filter(fecha_corte__lte=hasta)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = CorteInventarioCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        corte = CorteInventarioService.generar_corte_global(
            empresa=self.get_empresa(),
            usuario=request.user,
            fecha_corte=serializer.validated_data["fecha_corte"],
            observaciones=serializer.validated_data.get("observaciones", ""),
        )
        output = self.get_serializer(corte)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def cierre_mensual(self, request):
        serializer = CorteInventarioCierreMensualSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        corte = CorteInventarioService.generar_cierre_mensual(
            empresa=self.get_empresa(),
            usuario=request.user,
            periodo=serializer.validated_data["periodo"],
            observaciones=serializer.validated_data.get("observaciones", ""),
        )
        output = self.get_serializer(corte)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def items(self, request, pk=None):
        corte = CorteInventarioService.obtener_corte(corte_id=pk, empresa=self.get_empresa())
        queryset = corte.items.all().order_by("producto_nombre", "bodega_nombre", "id")

        producto_id = request.query_params.get("producto_id")
        bodega_id = request.query_params.get("bodega_id")
        q = request.query_params.get("q")
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        if q:
            queryset = queryset.filter(
                Q(producto_nombre__icontains=q)
                | Q(producto_sku__icontains=q)
                | Q(bodega_nombre__icontains=q)
                | Q(lotes_activos__icontains=q)
            )

        paginator = InventarioCorteItemPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CorteInventarioItemSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AjusteInventarioMasivoViewSet(TenantViewSetMixin, ModelViewSet):
    model = AjusteInventarioMasivo
    serializer_class = AjusteInventarioMasivoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "duplicar": Acciones.EDITAR,
        "confirmar": Acciones.EDITAR,
        "bulk_import": Acciones.EDITAR,
        "bulk_template": Acciones.VER,
    }
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related("items__producto", "items__bodega", "items__movimiento")
        estado = self.request.query_params.get("estado")
        desde = _parse_inventario_instant(self.request.query_params.get("desde"))
        hasta = _parse_inventario_instant(self.request.query_params.get("hasta"), end_of_day=True)
        q = self.request.query_params.get("q")

        if estado:
            queryset = queryset.filter(estado=estado)
        if desde is not None:
            queryset = queryset.filter(confirmado_en__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(confirmado_en__lte=hasta)
        if q:
            queryset = queryset.filter(Q(numero__icontains=q) | Q(referencia__icontains=q) | Q(motivo__icontains=q))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = AjusteInventarioMasivoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        estado = payload.pop("estado", None)
        if estado == EstadoDocumentoInventario.BORRADOR:
            documento = DocumentoInventarioService.guardar_borrador_ajuste_masivo(
                empresa=self.get_empresa(),
                usuario=request.user,
                **payload,
            )
        else:
            documento = DocumentoInventarioService.crear_ajuste_masivo(
                empresa=self.get_empresa(),
                usuario=request.user,
                **payload,
            )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = AjusteInventarioMasivoUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        documento = DocumentoInventarioService.actualizar_borrador_ajuste_masivo(
            documento_id=self.get_object().id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        DocumentoInventarioService.eliminar_borrador_ajuste_masivo(
            documento_id=self.get_object().id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        documento = DocumentoInventarioService.duplicar_ajuste_masivo(
            documento_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        documento = DocumentoInventarioService.confirmar_ajuste_masivo(
            documento_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        payload, documento = import_ajustes_masivos_desde_archivo(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
            dry_run=self._is_truthy(request.data.get("dry_run")),
        )
        if documento is not None:
            payload["documento"] = self.get_serializer(documento).data
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        content = build_ajustes_masivos_bulk_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_ajustes_masivos_inventario.xlsx"'
        return response


class TrasladoInventarioMasivoViewSet(TenantViewSetMixin, ModelViewSet):
    model = TrasladoInventarioMasivo
    serializer_class = TrasladoInventarioMasivoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.INVENTARIO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "duplicar": Acciones.EDITAR,
        "confirmar": Acciones.EDITAR,
        "bulk_import": Acciones.EDITAR,
        "bulk_template": Acciones.VER,
    }
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("bodega_origen", "bodega_destino")
            .prefetch_related("items__producto", "items__movimiento_salida", "items__movimiento_entrada")
        )
        estado = self.request.query_params.get("estado")
        desde = _parse_inventario_instant(self.request.query_params.get("desde"))
        hasta = _parse_inventario_instant(self.request.query_params.get("hasta"), end_of_day=True)
        q = self.request.query_params.get("q")

        if estado:
            queryset = queryset.filter(estado=estado)
        if desde is not None:
            queryset = queryset.filter(confirmado_en__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(confirmado_en__lte=hasta)
        if q:
            queryset = queryset.filter(Q(numero__icontains=q) | Q(referencia__icontains=q) | Q(motivo__icontains=q))
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = TrasladoInventarioMasivoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        estado = payload.pop("estado", None)
        if estado == EstadoDocumentoInventario.BORRADOR:
            documento = DocumentoInventarioService.guardar_borrador_traslado_masivo(
                empresa=self.get_empresa(),
                usuario=request.user,
                **payload,
            )
        else:
            documento = DocumentoInventarioService.crear_traslado_masivo(
                empresa=self.get_empresa(),
                usuario=request.user,
                **payload,
            )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = TrasladoInventarioMasivoUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        documento = DocumentoInventarioService.actualizar_borrador_traslado_masivo(
            documento_id=self.get_object().id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        DocumentoInventarioService.eliminar_borrador_traslado_masivo(
            documento_id=self.get_object().id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        documento = DocumentoInventarioService.duplicar_traslado_masivo(
            documento_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        documento = DocumentoInventarioService.confirmar_traslado_masivo(
            documento_id=pk,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        output = self.get_serializer(documento)
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        payload, documento = import_traslados_masivos_desde_archivo(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
            dry_run=self._is_truthy(request.data.get("dry_run")),
        )
        if documento is not None:
            payload["documento"] = self.get_serializer(documento).data
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        content = build_traslados_masivos_bulk_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_traslados_masivos_inventario.xlsx"'
        return response
