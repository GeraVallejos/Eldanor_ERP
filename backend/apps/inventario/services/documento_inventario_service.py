from decimal import Decimal
from uuid import uuid4

from django.db import transaction

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.inventario.models import (
    AjusteInventarioMasivo,
    AjusteInventarioMasivoItem,
    EstadoDocumentoInventario,
    TrasladoInventarioMasivo,
    TrasladoInventarioMasivoItem,
)
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Producto


class DocumentoInventarioService:
    """Servicio de aplicacion para documentos masivos de ajuste y traslado de inventario."""

    source = "inventario.documento_inventario_service"

    @staticmethod
    def _generate_number(prefix):
        """Genera un numero legible y suficientemente estable para documentos operativos."""
        return f"{prefix}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _serialize_decimal(value):
        """Serializa decimales a string estable para payloads y auditoria."""
        return str(Decimal(value).quantize(Decimal("0.01")))

    @staticmethod
    def _build_reference(base_reference, producto_label):
        """Compone una referencia de linea legible para trazabilidad documental."""
        return f"{base_reference} | {producto_label}".strip()

    @staticmethod
    def _record_side_effects(*, empresa, usuario, aggregate_type, aggregate_id, event_name, summary, payload):
        """Registra eventos de dominio, outbox y auditoria para documentos masivos."""
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_name,
            payload=payload,
            meta={"source": DocumentoInventarioService.source},
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="inventario.documentos_masivos",
            event_name=event_name,
            payload=payload,
            usuario=usuario,
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=Modulos.INVENTARIO,
            action_code=Acciones.EDITAR,
            event_type=event_name.upper().replace(".", "_"),
            entity_type=aggregate_type.upper(),
            entity_id=str(aggregate_id),
            summary=summary,
            severity=AuditSeverity.INFO,
            changes={},
            payload=payload,
            source=DocumentoInventarioService.source,
        )

    @classmethod
    @transaction.atomic
    def crear_ajuste_masivo(cls, *, empresa, usuario, referencia, motivo, observaciones="", items):
        """Crea y confirma un ajuste masivo aplicando regularizaciones por cada linea."""
        if not items:
            raise BusinessRuleError("Debe informar al menos una linea para el ajuste masivo.")

        documento = AjusteInventarioMasivo.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=cls._generate_number("AJM"),
            estado=EstadoDocumentoInventario.CONFIRMADO,
            referencia=referencia,
            motivo=motivo,
            observaciones=observaciones or "",
            subtotal=Decimal("0"),
            total=Decimal("0"),
        )

        lineas_payload = []
        total_diferencia = Decimal("0")

        for idx, item in enumerate(items, start=1):
            preview = InventarioService.previsualizar_regularizacion_stock(
                producto_id=item["producto_id"],
                bodega_id=item.get("bodega_id"),
                stock_objetivo=item["stock_objetivo"],
                empresa=empresa,
            )
            if not preview["ajustable"]:
                raise BusinessRuleError(
                    f"La linea {idx} no puede ajustarse: {' '.join(preview.get('warnings') or [])}".strip()
                )
            if Decimal(preview["diferencia"]) == 0:
                raise BusinessRuleError(f"La linea {idx} no genera diferencia de stock y debe omitirse.")

            producto_label = preview.get("producto_nombre") or str(item["producto_id"])
            referencia_linea = cls._build_reference(referencia, producto_label)
            movimiento = InventarioService.regularizar_stock(
                producto_id=item["producto_id"],
                bodega_id=item.get("bodega_id"),
                stock_objetivo=item["stock_objetivo"],
                referencia=referencia_linea,
                empresa=empresa,
                usuario=usuario,
                documento_id=documento.id,
            )
            AjusteInventarioMasivoItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                documento=documento,
                producto_id=item["producto_id"],
                bodega_id=item.get("bodega_id"),
                stock_objetivo=item["stock_objetivo"],
                stock_actual=preview["stock_actual"],
                diferencia=preview["diferencia"],
                movimiento=movimiento,
            )
            total_diferencia += abs(Decimal(preview["diferencia"]))
            lineas_payload.append(
                {
                    "producto_id": str(item["producto_id"]),
                    "bodega_id": str(item.get("bodega_id")) if item.get("bodega_id") else None,
                    "stock_actual": cls._serialize_decimal(preview["stock_actual"]),
                    "stock_objetivo": cls._serialize_decimal(item["stock_objetivo"]),
                    "diferencia": cls._serialize_decimal(preview["diferencia"]),
                    "movimiento_id": str(movimiento.id),
                }
            )

        documento.subtotal = total_diferencia
        documento.total = total_diferencia
        documento.save(skip_clean=True, update_fields=["subtotal", "total", "actualizado_en"])

        payload = {
            "documento_id": str(documento.id),
            "numero": documento.numero,
            "tipo": "AJUSTE_MASIVO",
            "referencia": documento.referencia,
            "motivo": documento.motivo,
            "items_count": len(lineas_payload),
            "lineas": lineas_payload,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="AjusteInventarioMasivo",
            aggregate_id=documento.id,
            event_name="inventario.ajuste_masivo.confirmado",
            summary=f"Ajuste masivo {documento.numero} confirmado.",
            payload=payload,
        )
        return documento

    @classmethod
    @transaction.atomic
    def duplicar_ajuste_masivo(cls, *, documento_id, empresa, usuario):
        """Duplica un ajuste masivo repitiendo el impacto original de cada linea."""
        documento = (
            AjusteInventarioMasivo.all_objects
            .prefetch_related("items")
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise BusinessRuleError("Ajuste masivo no encontrado para duplicar.")

        items = []
        for item in documento.items.all():
            preview = InventarioService.previsualizar_regularizacion_stock(
                producto_id=item.producto_id,
                bodega_id=item.bodega_id,
                stock_objetivo=item.stock_actual,
                empresa=empresa,
            )
            stock_objetivo = Decimal(preview["stock_actual"]) + Decimal(item.diferencia)
            items.append(
                {
                    "producto_id": item.producto_id,
                    "bodega_id": item.bodega_id,
                    "stock_objetivo": stock_objetivo,
                }
            )
        return cls.crear_ajuste_masivo(
            empresa=empresa,
            usuario=usuario,
            referencia=f"{documento.referencia} | DUPLICADO",
            motivo=documento.motivo,
            observaciones=documento.observaciones,
            items=items,
        )

    @classmethod
    @transaction.atomic
    def crear_traslado_masivo(
        cls,
        *,
        empresa,
        usuario,
        referencia,
        motivo,
        observaciones="",
        bodega_origen_id,
        bodega_destino_id,
        items,
    ):
        """Crea y confirma un traslado masivo aplicando traslados unitarios por linea."""
        if not items:
            raise BusinessRuleError("Debe informar al menos una linea para el traslado masivo.")

        documento = TrasladoInventarioMasivo.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=cls._generate_number("TRM"),
            estado=EstadoDocumentoInventario.CONFIRMADO,
            referencia=referencia,
            motivo=motivo,
            observaciones=observaciones or "",
            bodega_origen_id=bodega_origen_id,
            bodega_destino_id=bodega_destino_id,
            subtotal=Decimal("0"),
            total=Decimal("0"),
        )

        total_cantidad = Decimal("0")
        lineas_payload = []
        productos = {
            str(producto.id): producto.nombre
            for producto in Producto.all_objects.filter(
                empresa=empresa,
                id__in=[item["producto_id"] for item in items],
            ).only("id", "nombre")
        }

        for idx, item in enumerate(items, start=1):
            cantidad = Decimal(item["cantidad"])
            if cantidad <= 0:
                raise BusinessRuleError(f"La linea {idx} debe informar una cantidad mayor a cero.")

            referencia_linea = cls._build_reference(
                referencia,
                productos.get(str(item["producto_id"]), str(item["producto_id"])),
            )
            traslado = InventarioService.trasladar_stock(
                producto_id=item["producto_id"],
                bodega_origen_id=bodega_origen_id,
                bodega_destino_id=bodega_destino_id,
                cantidad=cantidad,
                referencia=referencia_linea,
                empresa=empresa,
                usuario=usuario,
                documento_id=documento.id,
            )
            TrasladoInventarioMasivoItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                documento=documento,
                producto_id=item["producto_id"],
                cantidad=cantidad,
                movimiento_salida=traslado["movimiento_salida"],
                movimiento_entrada=traslado["movimiento_entrada"],
            )
            total_cantidad += cantidad
            lineas_payload.append(
                {
                    "producto_id": str(item["producto_id"]),
                    "producto_nombre": traslado["movimiento_salida"].producto.nombre,
                    "cantidad": cls._serialize_decimal(cantidad),
                    "movimiento_salida_id": str(traslado["movimiento_salida"].id),
                    "movimiento_entrada_id": str(traslado["movimiento_entrada"].id),
                }
            )

        documento.subtotal = total_cantidad
        documento.total = total_cantidad
        documento.save(skip_clean=True, update_fields=["subtotal", "total", "actualizado_en"])

        payload = {
            "documento_id": str(documento.id),
            "numero": documento.numero,
            "tipo": "TRASLADO_MASIVO",
            "referencia": documento.referencia,
            "motivo": documento.motivo,
            "bodega_origen_id": str(documento.bodega_origen_id),
            "bodega_destino_id": str(documento.bodega_destino_id),
            "items_count": len(lineas_payload),
            "lineas": lineas_payload,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="TrasladoInventarioMasivo",
            aggregate_id=documento.id,
            event_name="inventario.traslado_masivo.confirmado",
            summary=f"Traslado masivo {documento.numero} confirmado.",
            payload=payload,
        )
        return documento

    @classmethod
    @transaction.atomic
    def duplicar_traslado_masivo(cls, *, documento_id, empresa, usuario):
        """Duplica un traslado masivo confirmado reutilizando origen, destino y lineas."""
        documento = (
            TrasladoInventarioMasivo.all_objects
            .prefetch_related("items")
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise BusinessRuleError("Traslado masivo no encontrado para duplicar.")

        items = [
            {
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
            }
            for item in documento.items.all()
        ]
        return cls.crear_traslado_masivo(
            empresa=empresa,
            usuario=usuario,
            referencia=f"{documento.referencia} | DUPLICADO",
            motivo=documento.motivo,
            observaciones=documento.observaciones,
            bodega_origen_id=documento.bodega_origen_id,
            bodega_destino_id=documento.bodega_destino_id,
            items=items,
        )
