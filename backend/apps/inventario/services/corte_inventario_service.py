import calendar
from decimal import Decimal
from datetime import date
from uuid import uuid4

from django.db import models
from django.db import transaction

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.inventario.models import (
    CorteInventario,
    CorteInventarioItem,
    EstadoCorteInventario,
    Bodega,
    ReservaStock,
    StockLote,
    StockProducto,
    StockSerie,
    TipoCorteInventario,
)
from apps.productos.models import Producto


class CorteInventarioService:
    """Servicio de aplicacion para cortes globales y auditables de inventario."""

    source = "inventario.corte_inventario_service"

    @staticmethod
    def _generate_number():
        """Genera un numero legible para cortes operativos de inventario."""
        return f"CIN-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _serialize_decimal(value):
        """Serializa decimales con precision estable para eventos y auditoria."""
        return str(Decimal(value).quantize(Decimal("0.01")))

    @staticmethod
    def _serialize_item(item):
        """Convierte una linea del corte a un payload estable de auditoria."""
        return {
            "producto_id": str(item.producto_id),
            "producto_nombre": item.producto_nombre,
            "producto_sku": item.producto_sku,
            "bodega_id": str(item.bodega_id),
            "bodega_nombre": item.bodega_nombre,
            "stock": CorteInventarioService._serialize_decimal(item.stock),
            "reservado": CorteInventarioService._serialize_decimal(item.reservado),
            "disponible": CorteInventarioService._serialize_decimal(item.disponible),
            "valor_stock": CorteInventarioService._serialize_decimal(item.valor_stock),
            "costo_promedio": str(item.costo_promedio),
            "lotes_activos": item.lotes_activos,
            "proximo_vencimiento": item.proximo_vencimiento.isoformat() if item.proximo_vencimiento else None,
            "series_disponibles": item.series_disponibles,
            "series_muestra": item.series_muestra,
        }

    @staticmethod
    def _parse_periodo_mensual(periodo):
        """Valida un periodo contable YYYY-MM y retorna periodo normalizado y fecha de cierre."""
        raw = str(periodo or "").strip()
        if len(raw) != 7 or raw[4] != "-":
            raise BusinessRuleError("El periodo debe usar formato YYYY-MM.")
        try:
            year = int(raw[:4])
            month = int(raw[5:7])
        except ValueError as exc:
            raise BusinessRuleError("El periodo debe usar formato YYYY-MM.") from exc
        if month < 1 or month > 12:
            raise BusinessRuleError("El mes del periodo contable no es valido.")
        day = calendar.monthrange(year, month)[1]
        return raw, date(year, month, day)

    @staticmethod
    def _record_side_effects(*, empresa, usuario, corte, event_name, summary, payload):
        """Registra eventos de dominio, outbox y auditoria del corte global."""
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="CorteInventario",
            aggregate_id=corte.id,
            event_type=event_name,
            payload=payload,
            meta={"source": CorteInventarioService.source},
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="inventario.cortes",
            event_name=event_name,
            payload=payload,
            usuario=usuario,
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=Modulos.INVENTARIO,
            action_code=Acciones.CREAR,
            event_type=event_name.upper().replace(".", "_"),
            entity_type="CORTE_INVENTARIO",
            entity_id=str(corte.id),
            summary=summary,
            severity=AuditSeverity.INFO,
            changes={},
            payload=payload,
            source=CorteInventarioService.source,
        )

    @staticmethod
    def obtener_corte(*, corte_id, empresa):
        """Obtiene un corte del tenant o levanta not found de dominio."""
        corte = (
            CorteInventario.all_objects
            .prefetch_related("items")
            .filter(id=corte_id, empresa=empresa)
            .first()
        )
        if not corte:
            raise ResourceNotFoundError("Corte de inventario no encontrado.")
        return corte

    @classmethod
    @transaction.atomic
    def generar_corte_global(
        cls,
        *,
        empresa,
        usuario,
        fecha_corte,
        observaciones="",
        tipo_corte=TipoCorteInventario.MANUAL,
        periodo_referencia="",
    ):
        """Genera una foto global del inventario actual con detalle por producto y bodega."""
        stock_rows = list(
            StockProducto.all_objects.filter(empresa=empresa, producto__activo=True)
            .select_related("producto__categoria", "bodega")
            .order_by("producto__nombre", "bodega__nombre")
        )
        reservas_qs = ReservaStock.all_objects.filter(empresa=empresa, producto__activo=True)

        stock_map = {(str(row.producto_id), str(row.bodega_id)): row for row in stock_rows}
        reservas_map = {}
        for reserva in reservas_qs.values("producto_id", "bodega_id").annotate(total=models.Sum("cantidad")):
            reservas_map[(str(reserva["producto_id"]), str(reserva["bodega_id"]))] = reserva["total"] or Decimal("0")

        keys = set(stock_map.keys()) | set(reservas_map.keys())
        if not keys:
            raise BusinessRuleError("No hay stock ni reservas activas para generar un corte global de inventario.")

        producto_ids = {key[0] for key in keys}
        bodega_ids = {key[1] for key in keys}
        productos = {
            str(producto.id): producto
            for producto in Producto.all_objects.filter(empresa=empresa, id__in=producto_ids).select_related("categoria")
        }
        bodegas = {
            str(bodega.id): bodega
            for bodega in Bodega.all_objects.filter(empresa=empresa, id__in=bodega_ids)
        }

        lotes_map = {}
        for lote in (
            StockLote.all_objects.filter(empresa=empresa, producto_id__in=producto_ids, bodega_id__in=bodega_ids, stock__gt=0)
            .values("producto_id", "bodega_id", "lote_codigo", "fecha_vencimiento")
            .order_by("lote_codigo")
        ):
            key = (str(lote["producto_id"]), str(lote["bodega_id"]))
            bucket = lotes_map.setdefault(key, {"codes": [], "next_expiry": None})
            codigo = lote["lote_codigo"] or ""
            if codigo and codigo not in bucket["codes"]:
                bucket["codes"].append(codigo)
            vencimiento = lote.get("fecha_vencimiento")
            if vencimiento and (bucket["next_expiry"] is None or vencimiento < bucket["next_expiry"]):
                bucket["next_expiry"] = vencimiento

        series_map = {}
        for serie in (
            StockSerie.all_objects.filter(
                empresa=empresa,
                producto_id__in=producto_ids,
                bodega_id__in=bodega_ids,
                estado="DISPONIBLE",
            )
            .values("producto_id", "bodega_id", "serie_codigo")
            .order_by("serie_codigo")
        ):
            key = (str(serie["producto_id"]), str(serie["bodega_id"]))
            bucket = series_map.setdefault(key, {"count": 0, "sample": []})
            bucket["count"] += 1
            codigo = serie.get("serie_codigo") or ""
            if codigo and len(bucket["sample"]) < 3:
                bucket["sample"].append(codigo)

        corte = CorteInventario.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=cls._generate_number(),
            estado=EstadoCorteInventario.GENERADO,
            tipo_corte=tipo_corte,
            periodo_referencia=periodo_referencia or "",
            fecha_corte=fecha_corte,
            observaciones=observaciones or "",
            subtotal=Decimal("0"),
            total=Decimal("0"),
            reservado_total=Decimal("0"),
            disponible_total=Decimal("0"),
            items_count=0,
        )

        total_stock = Decimal("0")
        total_reservado = Decimal("0")
        total_disponible = Decimal("0")
        total_valor = Decimal("0")
        serialized_items = []

        for producto_id, bodega_id in sorted(
            keys,
            key=lambda value: (
                productos.get(value[0]).nombre if productos.get(value[0]) else "",
                bodegas.get(value[1]).nombre if bodegas.get(value[1]) else "",
            ),
        ):
            stock_row = stock_map.get((producto_id, bodega_id))
            producto = productos.get(producto_id)
            bodega = bodegas.get(bodega_id)
            if not producto or not bodega:
                continue

            stock = Decimal(stock_row.stock if stock_row else 0)
            valor_stock = Decimal(stock_row.valor_stock if stock_row else 0)
            reservado = Decimal(reservas_map.get((producto_id, bodega_id), Decimal("0")))
            disponible = stock - reservado
            costo_promedio = Decimal("0")
            if stock > 0 and valor_stock:
                costo_promedio = (valor_stock / stock).quantize(Decimal("0.0001"))

            lotes_info = lotes_map.get((producto_id, bodega_id), {})
            series_info = series_map.get((producto_id, bodega_id), {})

            item = CorteInventarioItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                corte=corte,
                producto=producto,
                bodega=bodega,
                producto_nombre=producto.nombre,
                producto_sku=producto.sku or "",
                producto_categoria_nombre=producto.categoria.nombre if producto.categoria else "",
                bodega_nombre=bodega.nombre,
                stock=stock,
                reservado=reservado,
                disponible=disponible,
                costo_promedio=costo_promedio,
                valor_stock=valor_stock,
                lotes_activos=", ".join(lotes_info.get("codes", [])),
                proximo_vencimiento=lotes_info.get("next_expiry"),
                series_disponibles=series_info.get("count", 0),
                series_muestra=", ".join(series_info.get("sample", [])),
            )
            serialized_items.append(cls._serialize_item(item))
            total_stock += stock
            total_reservado += reservado
            total_disponible += disponible
            total_valor += valor_stock

        corte.subtotal = total_stock
        corte.total = total_valor
        corte.reservado_total = total_reservado
        corte.disponible_total = total_disponible
        corte.items_count = len(serialized_items)
        corte.save(
            skip_clean=True,
            update_fields=[
                "subtotal",
                "total",
                "reservado_total",
                "disponible_total",
                "items_count",
                "actualizado_en",
            ],
        )

        payload = {
            "corte_id": str(corte.id),
            "numero": corte.numero,
            "tipo_corte": corte.tipo_corte,
            "periodo_referencia": corte.periodo_referencia,
            "fecha_corte": corte.fecha_corte.isoformat(),
            "items_count": corte.items_count,
            "stock_total": cls._serialize_decimal(total_stock),
            "reservado_total": cls._serialize_decimal(total_reservado),
            "disponible_total": cls._serialize_decimal(total_disponible),
            "valor_total": cls._serialize_decimal(total_valor),
            "lineas_preview": serialized_items[:20],
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            corte=corte,
            event_name="inventario.corte_global.generado",
            summary=f"Corte global {corte.numero} generado para {corte.fecha_corte:%d/%m/%Y}.",
            payload=payload,
        )
        return corte

    @classmethod
    @transaction.atomic
    def generar_cierre_mensual(cls, *, empresa, usuario, periodo, observaciones=""):
        """Genera el cierre contable mensual del inventario para un periodo YYYY-MM."""
        periodo_normalizado, fecha_corte = cls._parse_periodo_mensual(periodo)
        existente = CorteInventario.all_objects.filter(
            empresa=empresa,
            tipo_corte=TipoCorteInventario.CIERRE_MENSUAL,
            periodo_referencia=periodo_normalizado,
        ).first()
        if existente:
            raise ConflictError(
                f"Ya existe un cierre mensual de inventario para {periodo_normalizado}.",
                meta={"corte_id": str(existente.id), "numero": existente.numero},
            )

        observaciones_finales = str(observaciones or "").strip()
        if not observaciones_finales:
            observaciones_finales = f"Cierre contable de inventario {periodo_normalizado}"

        return cls.generar_corte_global(
            empresa=empresa,
            usuario=usuario,
            fecha_corte=fecha_corte,
            observaciones=observaciones_finales,
            tipo_corte=TipoCorteInventario.CIERRE_MENSUAL,
            periodo_referencia=periodo_normalizado,
        )
