from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
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
    def _prepare_ajuste_item_values(*, empresa, item):
        """Calcula stock actual y diferencia estimada para una linea de ajuste en borrador."""
        preview = InventarioService.previsualizar_regularizacion_stock(
            producto_id=item["producto_id"],
            bodega_id=item.get("bodega_id"),
            stock_objetivo=item["stock_objetivo"],
            empresa=empresa,
        )
        return {
            "stock_actual": Decimal(preview["stock_actual"]),
            "diferencia": Decimal(preview["diferencia"]),
        }

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

    @staticmethod
    def _get_ajuste_documento(*, documento_id, empresa):
        """Obtiene un ajuste masivo del tenant o levanta not found de dominio."""
        documento = (
            AjusteInventarioMasivo.all_objects
            .prefetch_related("items")
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Ajuste masivo no encontrado.")
        return documento

    @staticmethod
    def _get_traslado_documento(*, documento_id, empresa):
        """Obtiene un traslado masivo del tenant o levanta not found de dominio."""
        documento = (
            TrasladoInventarioMasivo.all_objects
            .prefetch_related("items")
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Traslado masivo no encontrado.")
        return documento

    @classmethod
    @transaction.atomic
    def actualizar_borrador_ajuste_masivo(cls, *, documento_id, empresa, usuario, data):
        """Actualiza un borrador de ajuste masivo reemplazando cabecera y lineas cuando corresponde."""
        documento = cls._get_ajuste_documento(documento_id=documento_id, empresa=empresa)
        if documento.estado != EstadoDocumentoInventario.BORRADOR:
            raise ConflictError("Solo se pueden editar ajustes masivos en borrador.")

        update_fields = []
        for field in ("referencia", "motivo", "observaciones"):
            if field in data:
                setattr(documento, field, data[field])
                update_fields.append(field)

        if "items" in data:
            items = data["items"] or []
            if not items:
                raise BusinessRuleError("Debe informar al menos una linea para el ajuste masivo.")
            documento.items.all().delete()
            for item in items:
                computed = cls._prepare_ajuste_item_values(empresa=empresa, item=item)
                AjusteInventarioMasivoItem.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    documento=documento,
                    producto_id=item["producto_id"],
                    bodega_id=item.get("bodega_id"),
                    stock_objetivo=item["stock_objetivo"],
                    lote_codigo=item.get("lote_codigo", ""),
                    fecha_vencimiento=item.get("fecha_vencimiento"),
                    stock_actual=computed["stock_actual"],
                    diferencia=computed["diferencia"],
                )

        if update_fields:
            documento.save(skip_clean=True, update_fields=[*update_fields, "actualizado_en"])

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="AjusteInventarioMasivo",
            aggregate_id=documento.id,
            event_name="inventario.ajuste_masivo.borrador_actualizado",
            summary=f"Borrador de ajuste masivo {documento.numero} actualizado.",
            payload={
                "documento_id": str(documento.id),
                "numero": documento.numero,
                "estado": documento.estado,
                "items_count": documento.items.count(),
                "updated_fields": sorted(list(data.keys())),
            },
        )
        return documento

    @classmethod
    @transaction.atomic
    def guardar_borrador_ajuste_masivo(cls, *, empresa, usuario, referencia, motivo, observaciones="", items):
        """Guarda un borrador de ajuste masivo sin impactar stock operativo."""
        if not items:
            raise BusinessRuleError("Debe informar al menos una linea para el ajuste masivo.")

        documento = AjusteInventarioMasivo.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=cls._generate_number("AJM"),
            estado=EstadoDocumentoInventario.BORRADOR,
            referencia=referencia,
            motivo=motivo,
            observaciones=observaciones or "",
            subtotal=Decimal("0"),
            total=Decimal("0"),
            confirmado_en=None,
        )
        for item in items:
            computed = cls._prepare_ajuste_item_values(empresa=empresa, item=item)
            AjusteInventarioMasivoItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                documento=documento,
                producto_id=item["producto_id"],
                bodega_id=item.get("bodega_id"),
                stock_objetivo=item["stock_objetivo"],
                lote_codigo=item.get("lote_codigo", ""),
                fecha_vencimiento=item.get("fecha_vencimiento"),
                stock_actual=computed["stock_actual"],
                diferencia=computed["diferencia"],
            )

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="AjusteInventarioMasivo",
            aggregate_id=documento.id,
            event_name="inventario.ajuste_masivo.borrador_guardado",
            summary=f"Borrador de ajuste masivo {documento.numero} guardado.",
            payload={"documento_id": str(documento.id), "numero": documento.numero, "estado": documento.estado},
        )
        return documento

    @classmethod
    @transaction.atomic
    def crear_ajuste_masivo(cls, *, empresa, usuario, referencia, motivo, observaciones="", items):
        """Crea y confirma un ajuste masivo aplicando regularizaciones por cada linea."""
        if not items:
            raise BusinessRuleError("Debe informar al menos una linea para el ajuste masivo.")
        documento = cls.guardar_borrador_ajuste_masivo(
            empresa=empresa,
            usuario=usuario,
            referencia=referencia,
            motivo=motivo,
            observaciones=observaciones,
            items=items,
        )
        return cls.confirmar_ajuste_masivo(documento_id=documento.id, empresa=empresa, usuario=usuario)

    @classmethod
    @transaction.atomic
    def confirmar_ajuste_masivo(cls, *, documento_id, empresa, usuario):
        """Confirma un borrador de ajuste masivo ejecutando sus regularizaciones."""
        documento = cls._get_ajuste_documento(documento_id=documento_id, empresa=empresa)
        if documento.estado != EstadoDocumentoInventario.BORRADOR:
            raise ConflictError("Solo se pueden confirmar ajustes masivos en borrador.")

        lineas_payload = []
        total_diferencia = Decimal("0")

        for idx, item in enumerate(documento.items.all(), start=1):
            preview = InventarioService.previsualizar_regularizacion_stock(
                producto_id=item.producto_id,
                bodega_id=item.bodega_id,
                stock_objetivo=item.stock_objetivo,
                empresa=empresa,
            )
            if not preview["ajustable"]:
                raise BusinessRuleError(
                    f"La linea {idx} no puede ajustarse: {' '.join(preview.get('warnings') or [])}".strip()
                )
            if Decimal(preview["diferencia"]) == 0:
                raise BusinessRuleError(f"La linea {idx} no genera diferencia de stock y debe omitirse.")

            producto_label = preview.get("producto_nombre") or str(item.producto_id)
            referencia_linea = cls._build_reference(documento.referencia, producto_label)
            movimiento = InventarioService.regularizar_stock(
                producto_id=item.producto_id,
                bodega_id=item.bodega_id,
                stock_objetivo=item.stock_objetivo,
                referencia=referencia_linea,
                empresa=empresa,
                usuario=usuario,
                documento_id=documento.id,
                lote_codigo=item.lote_codigo,
                fecha_vencimiento=item.fecha_vencimiento,
            )
            item.stock_actual = preview["stock_actual"]
            item.diferencia = preview["diferencia"]
            item.movimiento = movimiento
            item.save(update_fields=["stock_actual", "diferencia", "movimiento", "actualizado_en"], skip_clean=True)
            total_diferencia += abs(Decimal(preview["diferencia"]))
            lineas_payload.append(
                {
                    "producto_id": str(item.producto_id),
                    "bodega_id": str(item.bodega_id) if item.bodega_id else None,
                    "stock_actual": cls._serialize_decimal(preview["stock_actual"]),
                    "stock_objetivo": cls._serialize_decimal(item.stock_objetivo),
                    "lote_codigo": item.lote_codigo,
                    "fecha_vencimiento": item.fecha_vencimiento.isoformat() if item.fecha_vencimiento else None,
                    "diferencia": cls._serialize_decimal(preview["diferencia"]),
                    "movimiento_id": str(movimiento.id),
                }
            )

        documento.estado = EstadoDocumentoInventario.CONFIRMADO
        documento.confirmado_en = timezone.now()
        documento.subtotal = total_diferencia
        documento.total = total_diferencia
        documento.save(skip_clean=True, update_fields=["estado", "confirmado_en", "subtotal", "total", "actualizado_en"])

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
    def eliminar_borrador_ajuste_masivo(cls, *, documento_id, empresa, usuario):
        """Elimina un ajuste masivo en borrador sin afectar stock confirmado."""
        documento = cls._get_ajuste_documento(documento_id=documento_id, empresa=empresa)
        if documento.estado != EstadoDocumentoInventario.BORRADOR:
            raise ConflictError("Solo se pueden eliminar ajustes masivos en borrador.")

        numero = documento.numero
        items_count = documento.items.count()
        documento.delete()

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="AjusteInventarioMasivo",
            aggregate_id=documento_id,
            event_name="inventario.ajuste_masivo.borrador_eliminado",
            summary=f"Borrador de ajuste masivo {numero} eliminado.",
            payload={
                "documento_id": str(documento_id),
                "numero": numero,
                "estado": EstadoDocumentoInventario.BORRADOR,
                "items_count": items_count,
            },
        )

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
                    "lote_codigo": item.lote_codigo,
                    "fecha_vencimiento": item.fecha_vencimiento,
                }
            )
        return cls.guardar_borrador_ajuste_masivo(
            empresa=empresa,
            usuario=usuario,
            referencia=f"{documento.referencia} | DUPLICADO",
            motivo=documento.motivo,
            observaciones=documento.observaciones,
            items=items,
        )

    @classmethod
    @transaction.atomic
    def actualizar_borrador_traslado_masivo(cls, *, documento_id, empresa, usuario, data):
        """Actualiza un borrador de traslado masivo reemplazando cabecera y lineas cuando corresponde."""
        documento = cls._get_traslado_documento(documento_id=documento_id, empresa=empresa)
        if documento.estado != EstadoDocumentoInventario.BORRADOR:
            raise ConflictError("Solo se pueden editar traslados masivos en borrador.")

        update_fields = []
        for field in ("referencia", "motivo", "observaciones", "bodega_origen_id", "bodega_destino_id"):
            if field in data:
                setattr(documento, field, data[field])
                update_fields.append(field)

        if str(documento.bodega_origen_id) == str(documento.bodega_destino_id):
            raise BusinessRuleError("La bodega destino debe ser distinta a la bodega origen.")

        if "items" in data:
            items = data["items"] or []
            if not items:
                raise BusinessRuleError("Debe informar al menos una linea para el traslado masivo.")
            documento.items.all().delete()
            for item in items:
                TrasladoInventarioMasivoItem.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    documento=documento,
                    producto_id=item["producto_id"],
                    cantidad=item["cantidad"],
                )

        if update_fields:
            documento.save(skip_clean=True, update_fields=[*update_fields, "actualizado_en"])

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="TrasladoInventarioMasivo",
            aggregate_id=documento.id,
            event_name="inventario.traslado_masivo.borrador_actualizado",
            summary=f"Borrador de traslado masivo {documento.numero} actualizado.",
            payload={
                "documento_id": str(documento.id),
                "numero": documento.numero,
                "estado": documento.estado,
                "items_count": documento.items.count(),
                "updated_fields": sorted(list(data.keys())),
            },
        )
        return documento

    @classmethod
    @transaction.atomic
    def guardar_borrador_traslado_masivo(
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
        """Guarda un borrador de traslado masivo sin mover stock entre bodegas."""
        if not items:
            raise BusinessRuleError("Debe informar al menos una linea para el traslado masivo.")

        documento = TrasladoInventarioMasivo.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=cls._generate_number("TRM"),
            estado=EstadoDocumentoInventario.BORRADOR,
            referencia=referencia,
            motivo=motivo,
            observaciones=observaciones or "",
            bodega_origen_id=bodega_origen_id,
            bodega_destino_id=bodega_destino_id,
            subtotal=Decimal("0"),
            total=Decimal("0"),
            confirmado_en=None,
        )
        for item in items:
            TrasladoInventarioMasivoItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                documento=documento,
                producto_id=item["producto_id"],
                cantidad=item["cantidad"],
            )

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="TrasladoInventarioMasivo",
            aggregate_id=documento.id,
            event_name="inventario.traslado_masivo.borrador_guardado",
            summary=f"Borrador de traslado masivo {documento.numero} guardado.",
            payload={"documento_id": str(documento.id), "numero": documento.numero, "estado": documento.estado},
        )
        return documento

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
        documento = cls.guardar_borrador_traslado_masivo(
            empresa=empresa,
            usuario=usuario,
            referencia=referencia,
            motivo=motivo,
            observaciones=observaciones,
            bodega_origen_id=bodega_origen_id,
            bodega_destino_id=bodega_destino_id,
            items=items,
        )
        return cls.confirmar_traslado_masivo(documento_id=documento.id, empresa=empresa, usuario=usuario)

    @classmethod
    @transaction.atomic
    def confirmar_traslado_masivo(cls, *, documento_id, empresa, usuario):
        """Confirma un borrador de traslado masivo ejecutando sus lineas unitarias."""
        documento = cls._get_traslado_documento(documento_id=documento_id, empresa=empresa)
        if documento.estado != EstadoDocumentoInventario.BORRADOR:
            raise ConflictError("Solo se pueden confirmar traslados masivos en borrador.")

        total_cantidad = Decimal("0")
        lineas_payload = []
        productos = {
            str(producto.id): producto.nombre
            for producto in Producto.all_objects.filter(
                empresa=empresa,
                id__in=[item.producto_id for item in documento.items.all()],
            ).only("id", "nombre")
        }

        for idx, item in enumerate(documento.items.all(), start=1):
            cantidad = Decimal(item.cantidad)
            if cantidad <= 0:
                raise BusinessRuleError(f"La linea {idx} debe informar una cantidad mayor a cero.")

            referencia_linea = cls._build_reference(
                documento.referencia,
                productos.get(str(item.producto_id), str(item.producto_id)),
            )
            traslado = InventarioService.trasladar_stock(
                producto_id=item.producto_id,
                bodega_origen_id=documento.bodega_origen_id,
                bodega_destino_id=documento.bodega_destino_id,
                cantidad=cantidad,
                referencia=referencia_linea,
                empresa=empresa,
                usuario=usuario,
                documento_id=documento.id,
            )
            item.movimiento_salida = traslado["movimiento_salida"]
            item.movimiento_entrada = traslado["movimiento_entrada"]
            item.save(update_fields=["movimiento_salida", "movimiento_entrada", "actualizado_en"], skip_clean=True)
            total_cantidad += cantidad
            lineas_payload.append(
                {
                    "producto_id": str(item.producto_id),
                    "producto_nombre": traslado["movimiento_salida"].producto.nombre,
                    "cantidad": cls._serialize_decimal(cantidad),
                    "movimiento_salida_id": str(traslado["movimiento_salida"].id),
                    "movimiento_entrada_id": str(traslado["movimiento_entrada"].id),
                }
            )

        documento.estado = EstadoDocumentoInventario.CONFIRMADO
        documento.confirmado_en = timezone.now()
        documento.subtotal = total_cantidad
        documento.total = total_cantidad
        documento.save(skip_clean=True, update_fields=["estado", "confirmado_en", "subtotal", "total", "actualizado_en"])

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
    def eliminar_borrador_traslado_masivo(cls, *, documento_id, empresa, usuario):
        """Elimina un traslado masivo en borrador sin mover stock entre bodegas."""
        documento = cls._get_traslado_documento(documento_id=documento_id, empresa=empresa)
        if documento.estado != EstadoDocumentoInventario.BORRADOR:
            raise ConflictError("Solo se pueden eliminar traslados masivos en borrador.")

        numero = documento.numero
        items_count = documento.items.count()
        documento.delete()

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="TrasladoInventarioMasivo",
            aggregate_id=documento_id,
            event_name="inventario.traslado_masivo.borrador_eliminado",
            summary=f"Borrador de traslado masivo {numero} eliminado.",
            payload={
                "documento_id": str(documento_id),
                "numero": numero,
                "estado": EstadoDocumentoInventario.BORRADOR,
                "items_count": items_count,
            },
        )

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
        return cls.guardar_borrador_traslado_masivo(
            empresa=empresa,
            usuario=usuario,
            referencia=f"{documento.referencia} | DUPLICADO",
            motivo=documento.motivo,
            observaciones=documento.observaciones,
            bodega_origen_id=documento.bodega_origen_id,
            bodega_destino_id=documento.bodega_destino_id,
            items=items,
        )
