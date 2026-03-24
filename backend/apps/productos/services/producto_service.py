import django.core.exceptions as django_exceptions
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.productos.models import Producto
from apps.productos.services.producto_snapshot_service import ProductoSnapshotService


class ProductoService:
    """Servicio de aplicacion para administrar el catalogo de productos con trazabilidad funcional."""

    AUDIT_FIELDS = (
        "nombre",
        "descripcion",
        "sku",
        "tipo",
        "categoria_id",
        "impuesto_id",
        "moneda_id",
        "precio_referencia",
        "precio_costo",
        "unidad_medida",
        "permite_decimales",
        "maneja_inventario",
        "stock_actual",
        "costo_promedio",
        "stock_minimo",
        "usa_lotes",
        "usa_series",
        "usa_vencimiento",
        "activo",
    )

    @staticmethod
    def _serialize_value(value):
        """Normaliza valores del agregado para payloads y auditoria sin ambiguedad de tipos."""
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _snapshot_producto(producto):
        """Obtiene una fotografia estable del producto para diff funcional."""
        snapshot = {}
        for field in ProductoService.AUDIT_FIELDS:
            snapshot[field] = ProductoService._serialize_value(getattr(producto, field))
        return snapshot

    @staticmethod
    def _build_changes(before, after):
        """Construye changes before/after solo para campos efectivamente modificados."""
        changes = {}
        for field in ProductoService.AUDIT_FIELDS:
            before_value = before.get(field)
            after_value = after.get(field)
            if before_value != after_value:
                changes[field] = [before_value, after_value]
        return changes

    @staticmethod
    def _translate_validation_error(exc):
        """Convierte ValidationError de Django al contrato AppError del dominio."""
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "messages"):
            detail = exc.messages
        else:
            detail = str(exc)
        return BusinessRuleError(detail, error_code="VALIDATION_ERROR")

    @staticmethod
    def _save_producto(producto, **kwargs):
        """Persiste producto traduciendo validaciones e integridad a excepciones de aplicacion."""
        try:
            producto.save(**kwargs)
            return producto
        except django_exceptions.ValidationError as exc:
            raise ProductoService._translate_validation_error(exc) from exc
        except IntegrityError as exc:
            raise ConflictError(
                "Ya existe un producto con el mismo nombre o SKU en la empresa activa.",
                meta={"source": "ProductoService"},
            ) from exc

    @staticmethod
    def _get_producto_for_update(*, producto_id, empresa):
        """Obtiene el producto con lock pesimista para cambios concurrentes sobre el catalogo."""
        producto = (
            Producto.all_objects.select_for_update()
            .filter(id=producto_id, empresa=empresa)
            .first()
        )
        if not producto:
            raise ResourceNotFoundError("Producto no encontrado.")
        return producto

    @staticmethod
    def _record_side_effects(*, empresa, usuario, producto, event_name, action_code, changes=None, extra_payload=None):
        """Registra domain event, outbox y auditoria de forma consistente para cambios del catalogo."""
        payload = {
            "producto_id": str(producto.id),
            "nombre": producto.nombre,
            "sku": producto.sku,
            "activo": producto.activo,
            "tipo": producto.tipo,
        }
        if extra_payload:
            payload.update(extra_payload)

        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="Producto",
            aggregate_id=producto.id,
            event_type=event_name,
            payload=payload,
            meta={"source": "ProductoService"},
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="productos.catalogo",
            event_name=event_name,
            payload=payload,
            usuario=usuario,
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=Modulos.PRODUCTOS,
            action_code=action_code,
            event_type=event_name.upper().replace(".", "_"),
            entity_type="PRODUCTO",
            entity_id=producto.id,
            summary=f"Cambio de catalogo sobre producto {producto.sku}.",
            severity=AuditSeverity.INFO,
            changes=changes or {},
            payload=payload,
            source="ProductoService",
        )

    @staticmethod
    def _record_snapshot(
        *,
        empresa,
        usuario,
        producto,
        event_name,
        snapshot,
        changes=None,
        producto_id_ref=None,
        attach_producto=True,
    ):
        """Registra una version inmutable del maestro luego de cada cambio funcional."""
        ProductoSnapshotService.registrar_snapshot(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_type=event_name,
            snapshot=snapshot,
            changes=changes or {},
            producto_id_ref=producto_id_ref,
            attach_producto=attach_producto,
        )

    @staticmethod
    @transaction.atomic
    def crear_producto(*, empresa, usuario, data):
        """Crea un producto del catalogo y registra trazabilidad funcional completa."""
        producto = Producto(empresa=empresa, creado_por=usuario, **data)
        ProductoService._save_producto(producto)

        snapshot = ProductoService._snapshot_producto(producto)
        ProductoService._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_name="producto.creado",
            action_code=Acciones.CREAR,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
            extra_payload={"changes_count": len(snapshot)},
        )
        ProductoService._record_snapshot(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_name="producto.creado",
            snapshot=snapshot,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return producto

    @staticmethod
    @transaction.atomic
    def actualizar_producto(*, producto_id, empresa, usuario, data):
        """Actualiza un producto existente aplicando lock y emitiendo solo cambios efectivos."""
        producto = ProductoService._get_producto_for_update(producto_id=producto_id, empresa=empresa)
        before = ProductoService._snapshot_producto(producto)

        for field, value in data.items():
            setattr(producto, field, value)

        after = ProductoService._snapshot_producto(producto)
        planned_changes = ProductoService._build_changes(before, after)
        if not planned_changes:
            return producto

        ProductoService._save_producto(producto)
        after = ProductoService._snapshot_producto(producto)
        changes = ProductoService._build_changes(before, after)
        if not changes:
            return producto

        ProductoService._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_name="producto.actualizado",
            action_code=Acciones.EDITAR,
            changes=changes,
            extra_payload={"changed_fields": sorted(changes.keys())},
        )
        ProductoService._record_snapshot(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_name="producto.actualizado",
            snapshot=after,
            changes=changes,
        )
        return producto

    @staticmethod
    @transaction.atomic
    def eliminar_producto(*, producto_id, empresa, usuario):
        """Elimina fisicamente o anula logicamente un producto segun su trazabilidad historica."""
        producto = ProductoService._get_producto_for_update(producto_id=producto_id, empresa=empresa)
        before = ProductoService._snapshot_producto(producto)
        producto_id = producto.id

        try:
            producto.delete()
        except ProtectedError as exc:
            if not producto.activo:
                raise ConflictError("El producto ya esta anulado y mantiene referencias historicas.") from exc

            # Conserva integridad historica cuando el producto ya fue usado.
            producto.activo = False
            ProductoService._save_producto(producto, skip_clean=True, update_fields=["activo"])
            after = ProductoService._snapshot_producto(producto)
            changes = ProductoService._build_changes(before, after)
            ProductoService._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                producto=producto,
                event_name="producto.anulado",
                action_code=Acciones.BORRAR,
                changes=changes,
                extra_payload={"deletion_mode": "SOFT"},
            )
            ProductoService._record_snapshot(
                empresa=empresa,
                usuario=usuario,
                producto=producto,
                event_name="producto.anulado",
                snapshot=after,
                changes=changes,
            )
            return {"deleted": False, "producto": producto}

        producto.id = producto_id
        ProductoService._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_name="producto.eliminado",
            action_code=Acciones.BORRAR,
            changes={field: [value, None] for field, value in before.items() if value is not None},
            extra_payload={"deletion_mode": "HARD"},
        )
        ProductoService._record_snapshot(
            empresa=empresa,
            usuario=usuario,
            producto=producto,
            event_name="producto.eliminado",
            snapshot={},
            changes={field: [value, None] for field, value in before.items() if value is not None},
            producto_id_ref=producto_id,
            attach_producto=False,
        )
        return {"deleted": True, "producto": None}
