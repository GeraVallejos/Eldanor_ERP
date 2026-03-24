import django.core.exceptions as django_exceptions
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.productos.models import Categoria, Impuesto


class _CatalogoBaseService:
    """Utilidades compartidas para trazabilidad de catalogos auxiliares del modulo productos."""

    module_code = Modulos.PRODUCTOS
    source = "productos.catalogo_service"

    @staticmethod
    def _serialize_value(value):
        """Convierte valores a una forma estable para auditoria y eventos."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def _snapshot(cls, instance, fields):
        """Construye un snapshot plano de los campos relevantes del agregado."""
        return {
            field: cls._serialize_value(getattr(instance, field))
            for field in fields
        }

    @staticmethod
    def _build_changes(before, after, fields):
        """Genera diff before/after solo para cambios efectivos."""
        changes = {}
        for field in fields:
            before_value = before.get(field)
            after_value = after.get(field)
            if before_value != after_value:
                changes[field] = [before_value, after_value]
        return changes

    @staticmethod
    def _translate_validation_error(exc):
        """Convierte ValidationError de Django al contrato de errores de aplicacion."""
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "messages"):
            detail = exc.messages
        else:
            detail = str(exc)
        return BusinessRuleError(detail, error_code="VALIDATION_ERROR")

    @classmethod
    def _save_instance(cls, instance, conflict_message, **kwargs):
        """Persiste el agregado traduciendo errores tecnicos a AppError."""
        try:
            instance.save(**kwargs)
            return instance
        except django_exceptions.ValidationError as exc:
            raise cls._translate_validation_error(exc) from exc
        except IntegrityError as exc:
            raise ConflictError(conflict_message, meta={"source": cls.source}) from exc

    @classmethod
    def _record_side_effects(
        cls,
        *,
        empresa,
        usuario,
        aggregate_type,
        aggregate_id,
        event_name,
        action_code,
        entity_type,
        summary,
        payload,
        changes=None,
        topic="productos.catalogo",
    ):
        """Registra eventos de dominio, outbox y auditoria de manera consistente."""
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_name,
            payload=payload,
            meta={"source": cls.source},
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic=topic,
            event_name=event_name,
            payload=payload,
            usuario=usuario,
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=cls.module_code,
            action_code=action_code,
            event_type=event_name.upper().replace(".", "_"),
            entity_type=entity_type,
            entity_id=aggregate_id,
            summary=summary,
            severity=AuditSeverity.INFO,
            changes=changes or {},
            payload=payload,
            source=cls.source,
        )


class CategoriaService(_CatalogoBaseService):
    """Servicio de aplicacion para categorias del maestro de productos."""

    audit_fields = ("nombre", "descripcion", "activa")

    @staticmethod
    def _get_categoria_for_update(*, categoria_id, empresa):
        """Obtiene la categoria con lock para cambios concurrentes del catalogo."""
        categoria = Categoria.all_objects.select_for_update().filter(id=categoria_id, empresa=empresa).first()
        if not categoria:
            raise ResourceNotFoundError("Categoria no encontrada.")
        return categoria

    @classmethod
    @transaction.atomic
    def crear_categoria(cls, *, empresa, usuario, data):
        """Crea una categoria y registra trazabilidad funcional del catalogo."""
        categoria = Categoria(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(categoria, "Ya existe una categoria con el mismo nombre en la empresa activa.")

        snapshot = cls._snapshot(categoria, cls.audit_fields)
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="CategoriaProducto",
            aggregate_id=categoria.id,
            event_name="categoria_producto.creada",
            action_code=Acciones.CREAR,
            entity_type="CATEGORIA_PRODUCTO",
            summary=f"Categoria {categoria.nombre} creada.",
            payload={"categoria_id": str(categoria.id), "nombre": categoria.nombre, "activa": categoria.activa},
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return categoria

    @classmethod
    @transaction.atomic
    def actualizar_categoria(cls, *, categoria_id, empresa, usuario, data):
        """Actualiza una categoria registrando solo cambios efectivos del maestro."""
        categoria = cls._get_categoria_for_update(categoria_id=categoria_id, empresa=empresa)
        before = cls._snapshot(categoria, cls.audit_fields)

        for field, value in data.items():
            setattr(categoria, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(categoria, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return categoria

        cls._save_instance(categoria, "Ya existe una categoria con el mismo nombre en la empresa activa.")
        after = cls._snapshot(categoria, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return categoria

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="CategoriaProducto",
            aggregate_id=categoria.id,
            event_name="categoria_producto.actualizada",
            action_code=Acciones.EDITAR,
            entity_type="CATEGORIA_PRODUCTO",
            summary=f"Categoria {categoria.nombre} actualizada.",
            payload={"categoria_id": str(categoria.id), "nombre": categoria.nombre, "activa": categoria.activa},
            changes=changes,
        )
        return categoria

    @classmethod
    @transaction.atomic
    def eliminar_categoria(cls, *, categoria_id, empresa, usuario):
        """Elimina o desactiva una categoria cuando mantiene referencias historicas."""
        categoria = cls._get_categoria_for_update(categoria_id=categoria_id, empresa=empresa)
        before = cls._snapshot(categoria, cls.audit_fields)
        categoria_pk = categoria.id

        try:
            categoria.delete()
        except ProtectedError as exc:
            if not categoria.activa:
                raise ConflictError("La categoria ya esta inactiva y mantiene referencias historicas.") from exc

            categoria.activa = False
            cls._save_instance(categoria, "No se pudo desactivar la categoria.", skip_clean=True, update_fields=["activa"])
            after = cls._snapshot(categoria, cls.audit_fields)
            changes = cls._build_changes(before, after, cls.audit_fields)
            cls._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                aggregate_type="CategoriaProducto",
                aggregate_id=categoria.id,
                event_name="categoria_producto.desactivada",
                action_code=Acciones.BORRAR,
                entity_type="CATEGORIA_PRODUCTO",
                summary=f"Categoria {categoria.nombre} desactivada.",
                payload={"categoria_id": str(categoria.id), "nombre": categoria.nombre, "activa": categoria.activa},
                changes=changes,
            )
            return {"deleted": False, "categoria": categoria}

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="CategoriaProducto",
            aggregate_id=categoria_pk,
            event_name="categoria_producto.eliminada",
            action_code=Acciones.BORRAR,
            entity_type="CATEGORIA_PRODUCTO",
            summary=f"Categoria {before.get('nombre')} eliminada.",
            payload={"categoria_id": str(categoria_pk), "nombre": before.get("nombre"), "activa": False},
            changes={field: [value, None] for field, value in before.items() if value is not None},
        )
        return {"deleted": True, "categoria": None}


class ImpuestoService(_CatalogoBaseService):
    """Servicio de aplicacion para impuestos del catalogo de productos."""

    audit_fields = ("nombre", "porcentaje", "activo")

    @staticmethod
    def _get_impuesto_for_update(*, impuesto_id, empresa):
        """Obtiene el impuesto con lock para asegurar actualizaciones consistentes."""
        impuesto = Impuesto.all_objects.select_for_update().filter(id=impuesto_id, empresa=empresa).first()
        if not impuesto:
            raise ResourceNotFoundError("Impuesto no encontrado.")
        return impuesto

    @classmethod
    @transaction.atomic
    def crear_impuesto(cls, *, empresa, usuario, data):
        """Crea un impuesto y registra trazabilidad de configuracion tributaria."""
        impuesto = Impuesto(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(
            impuesto,
            "Ya existe un impuesto con el mismo nombre o porcentaje en la empresa activa.",
        )

        snapshot = cls._snapshot(impuesto, cls.audit_fields)
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ImpuestoProducto",
            aggregate_id=impuesto.id,
            event_name="impuesto_producto.creado",
            action_code=Acciones.CREAR,
            entity_type="IMPUESTO_PRODUCTO",
            summary=f"Impuesto {impuesto.nombre} creado.",
            payload={
                "impuesto_id": str(impuesto.id),
                "nombre": impuesto.nombre,
                "porcentaje": str(impuesto.porcentaje),
                "activo": impuesto.activo,
            },
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return impuesto

    @classmethod
    @transaction.atomic
    def actualizar_impuesto(cls, *, impuesto_id, empresa, usuario, data):
        """Actualiza un impuesto y emite solo cambios efectivos para auditoria."""
        impuesto = cls._get_impuesto_for_update(impuesto_id=impuesto_id, empresa=empresa)
        before = cls._snapshot(impuesto, cls.audit_fields)

        for field, value in data.items():
            setattr(impuesto, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(impuesto, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return impuesto

        cls._save_instance(
            impuesto,
            "Ya existe un impuesto con el mismo nombre o porcentaje en la empresa activa.",
        )
        after = cls._snapshot(impuesto, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return impuesto

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ImpuestoProducto",
            aggregate_id=impuesto.id,
            event_name="impuesto_producto.actualizado",
            action_code=Acciones.EDITAR,
            entity_type="IMPUESTO_PRODUCTO",
            summary=f"Impuesto {impuesto.nombre} actualizado.",
            payload={
                "impuesto_id": str(impuesto.id),
                "nombre": impuesto.nombre,
                "porcentaje": str(impuesto.porcentaje),
                "activo": impuesto.activo,
            },
            changes=changes,
        )
        return impuesto

    @classmethod
    @transaction.atomic
    def eliminar_impuesto(cls, *, impuesto_id, empresa, usuario):
        """Elimina o inactiva un impuesto segun su uso historico dentro del ERP."""
        impuesto = cls._get_impuesto_for_update(impuesto_id=impuesto_id, empresa=empresa)
        before = cls._snapshot(impuesto, cls.audit_fields)
        impuesto_pk = impuesto.id

        try:
            impuesto.delete()
        except ProtectedError as exc:
            if not impuesto.activo:
                raise ConflictError("El impuesto ya esta inactivo y mantiene referencias historicas.") from exc

            impuesto.activo = False
            cls._save_instance(impuesto, "No se pudo inactivar el impuesto.", skip_clean=True, update_fields=["activo"])
            after = cls._snapshot(impuesto, cls.audit_fields)
            changes = cls._build_changes(before, after, cls.audit_fields)
            cls._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                aggregate_type="ImpuestoProducto",
                aggregate_id=impuesto.id,
                event_name="impuesto_producto.inactivado",
                action_code=Acciones.BORRAR,
                entity_type="IMPUESTO_PRODUCTO",
                summary=f"Impuesto {impuesto.nombre} inactivado.",
                payload={
                    "impuesto_id": str(impuesto.id),
                    "nombre": impuesto.nombre,
                    "porcentaje": str(impuesto.porcentaje),
                    "activo": impuesto.activo,
                },
                changes=changes,
            )
            return {"deleted": False, "impuesto": impuesto}

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ImpuestoProducto",
            aggregate_id=impuesto_pk,
            event_name="impuesto_producto.eliminado",
            action_code=Acciones.BORRAR,
            entity_type="IMPUESTO_PRODUCTO",
            summary=f"Impuesto {before.get('nombre')} eliminado.",
            payload={
                "impuesto_id": str(impuesto_pk),
                "nombre": before.get("nombre"),
                "porcentaje": before.get("porcentaje"),
                "activo": False,
            },
            changes={field: [value, None] for field, value in before.items() if value is not None},
        )
        return {"deleted": True, "impuesto": None}
