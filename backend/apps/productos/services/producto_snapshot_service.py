from decimal import Decimal

from django.db import IntegrityError, transaction

from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.productos.models import Categoria, Impuesto, ProductoSnapshot
from apps.tesoreria.models import Moneda


class ProductoSnapshotService:
    """Servicio de versionado, comparacion y restauracion del maestro de productos."""

    RESTORE_FIELDS = (
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
        "stock_minimo",
        "usa_lotes",
        "usa_series",
        "usa_vencimiento",
        "activo",
    )

    @staticmethod
    def _parse_bool(value):
        """Convierte valores serializados del snapshot a booleano funcional."""
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    @staticmethod
    def _parse_decimal(value):
        """Convierte montos serializados del snapshot a Decimal seguro."""
        if value in (None, ""):
            return Decimal("0")
        return Decimal(str(value))

    @staticmethod
    def _get_snapshot(*, empresa, producto_id, version):
        """Obtiene una version del maestro por producto y numero de version."""
        snapshot = (
            ProductoSnapshot.all_objects
            .select_related("producto")
            .filter(empresa=empresa, producto_id_ref=producto_id, version=version)
            .first()
        )
        if not snapshot:
            raise ResourceNotFoundError("Version de producto no encontrada.")
        return snapshot

    @classmethod
    def _build_changes(cls, from_snapshot, to_snapshot):
        """Compara dos snapshots funcionales y retorna solo diferencias efectivas."""
        all_fields = sorted(set(from_snapshot.keys()) | set(to_snapshot.keys()))
        changes = {}
        for field in all_fields:
            from_value = from_snapshot.get(field)
            to_value = to_snapshot.get(field)
            if from_value != to_value:
                changes[field] = [from_value, to_value]
        return changes

    @classmethod
    def _build_restore_data(cls, *, empresa, snapshot):
        """Reconstruye el payload del maestro desde una version historica."""
        data = {}
        raw = snapshot.snapshot or {}

        for field in cls.RESTORE_FIELDS:
            if field not in raw:
                continue
            value = raw.get(field)

            if field == "categoria_id":
                data["categoria"] = Categoria.all_objects.filter(empresa=empresa, id=value).first() if value else None
            elif field == "impuesto_id":
                data["impuesto"] = Impuesto.all_objects.filter(empresa=empresa, id=value).first() if value else None
            elif field == "moneda_id":
                data["moneda"] = Moneda.all_objects.filter(empresa=empresa, id=value).first() if value else None
            elif field in {"precio_referencia", "precio_costo", "stock_minimo"}:
                data[field] = cls._parse_decimal(value)
            elif field in {
                "permite_decimales",
                "maneja_inventario",
                "usa_lotes",
                "usa_series",
                "usa_vencimiento",
                "activo",
            }:
                data[field] = cls._parse_bool(value)
            else:
                data[field] = value

        return data

    @staticmethod
    def registrar_snapshot(
        *,
        empresa,
        usuario,
        producto,
        event_type,
        snapshot,
        changes=None,
        producto_id_ref=None,
        attach_producto=True,
    ):
        """Registra una nueva version inmutable del maestro despues de un cambio funcional."""
        producto_id_ref = producto_id_ref or producto.id
        ultima_version = (
            ProductoSnapshot.all_objects
            .filter(empresa=empresa, producto_id_ref=producto_id_ref)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        ) or 0

        try:
            return ProductoSnapshot.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                producto=producto if attach_producto and getattr(producto, "pk", None) else None,
                producto_id_ref=producto_id_ref,
                version=ultima_version + 1,
                event_type=event_type,
                changes=changes or {},
                snapshot=snapshot or {},
            )
        except IntegrityError as exc:
            raise ConflictError(
                "No se pudo registrar la nueva version del maestro de producto.",
                meta={"source": "ProductoSnapshotService"},
            ) from exc

    @classmethod
    def comparar_versiones(cls, *, empresa, producto_id, version_desde, version_hasta):
        """Compara dos versiones del maestro y retorna diferencias funcionales legibles."""
        if version_desde == version_hasta:
            raise BusinessRuleError(
                "Debe indicar dos versiones distintas para comparar.",
                error_code="VALIDATION_ERROR",
            )

        snapshot_desde = cls._get_snapshot(empresa=empresa, producto_id=producto_id, version=version_desde)
        snapshot_hasta = cls._get_snapshot(empresa=empresa, producto_id=producto_id, version=version_hasta)
        changes = cls._build_changes(snapshot_desde.snapshot or {}, snapshot_hasta.snapshot or {})

        return {
            "producto_id": str(producto_id),
            "version_desde": snapshot_desde.version,
            "version_hasta": snapshot_hasta.version,
            "event_type_desde": snapshot_desde.event_type,
            "event_type_hasta": snapshot_hasta.event_type,
            "changes": changes,
            "total_changes": len(changes),
        }

    @classmethod
    @transaction.atomic
    def restaurar_version(cls, *, empresa, usuario, producto_id, version):
        """Restaura una version historica del maestro usando el servicio principal del producto."""
        snapshot = cls._get_snapshot(empresa=empresa, producto_id=producto_id, version=version)
        if not snapshot.snapshot:
            raise BusinessRuleError(
                "No se puede restaurar una version sin snapshot funcional.",
                error_code="VALIDATION_ERROR",
            )

        from apps.productos.services.producto_service import ProductoService

        restore_data = cls._build_restore_data(empresa=empresa, snapshot=snapshot)
        producto = ProductoService.actualizar_producto(
            producto_id=producto_id,
            empresa=empresa,
            usuario=usuario,
            data=restore_data,
        )
        return {
            "producto": producto,
            "version_restaurada": snapshot.version,
        }
