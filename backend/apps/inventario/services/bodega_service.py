import django.core.exceptions as django_exceptions
from django.db import IntegrityError, transaction

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.inventario.models import Bodega


class BodegaService:
    """Servicio de aplicacion para el maestro de bodegas del modulo inventario."""

    module_code = Modulos.INVENTARIO
    source = "inventario.bodega_service"
    audit_fields = ("nombre", "activa")

    @staticmethod
    def _serialize_value(value):
        """Convierte valores a una representacion estable para auditoria y eventos."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def _snapshot(cls, instance):
        """Construye un snapshot plano de los campos auditables de la bodega."""
        return {
            field: cls._serialize_value(getattr(instance, field))
            for field in cls.audit_fields
        }

    @classmethod
    def _build_changes(cls, before, after):
        """Genera diferencias before/after solo para cambios efectivos."""
        changes = {}
        for field in cls.audit_fields:
            before_value = before.get(field)
            after_value = after.get(field)
            if before_value != after_value:
                changes[field] = [before_value, after_value]
        return changes

    @staticmethod
    def _translate_validation_error(exc):
        """Convierte ValidationError de Django al contrato de errores del ERP."""
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "messages"):
            detail = exc.messages
        else:
            detail = str(exc)
        return BusinessRuleError(detail, error_code="VALIDATION_ERROR")

    @classmethod
    def _save_instance(cls, instance, conflict_message, **kwargs):
        """Persiste la bodega traduciendo errores tecnicos a AppError."""
        try:
            instance.save(**kwargs)
            return instance
        except django_exceptions.ValidationError as exc:
            raise cls._translate_validation_error(exc) from exc
        except IntegrityError as exc:
            raise ConflictError(conflict_message, meta={"source": cls.source}) from exc

    @staticmethod
    def _get_bodega_for_update(*, bodega_id, empresa):
        """Obtiene una bodega con lock pesimista o levanta not found de dominio."""
        bodega = Bodega.all_objects.select_for_update().filter(id=bodega_id, empresa=empresa).first()
        if not bodega:
            raise ResourceNotFoundError("Bodega no encontrada.")
        return bodega

    @staticmethod
    def _tiene_referencias_historicas(bodega):
        """Determina si la bodega ya fue usada en inventario y debe preservarse."""
        return any(
            (
                bodega.movimientos.exists(),
                bodega.stocks.exists(),
                bodega.snapshots_inventario.exists(),
                bodega.reservas.exists(),
                bodega.stocks_lote.exists(),
                bodega.series.exists(),
            )
        )

    @classmethod
    def _record_side_effects(
        cls,
        *,
        empresa,
        usuario,
        aggregate_id,
        event_name,
        action_code,
        summary,
        payload,
        changes=None,
    ):
        """Registra domain events, outbox y auditoria para cambios del maestro."""
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="BodegaInventario",
            aggregate_id=aggregate_id,
            event_type=event_name,
            payload=payload,
            meta={"source": cls.source},
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="inventario.bodegas",
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
            entity_type="BODEGA_INVENTARIO",
            entity_id=aggregate_id,
            summary=summary,
            severity=AuditSeverity.INFO,
            changes=changes or {},
            payload=payload,
            source=cls.source,
        )

    @classmethod
    @transaction.atomic
    def crear_bodega(cls, *, empresa, usuario, data):
        """Crea una bodega activa o inactiva con trazabilidad funcional completa."""
        bodega = Bodega(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(bodega, "Ya existe una bodega con el mismo nombre en la empresa activa.")

        snapshot = cls._snapshot(bodega)
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_id=bodega.id,
            event_name="inventario.bodega.creada",
            action_code=Acciones.CREAR,
            summary=f"Bodega {bodega.nombre} creada.",
            payload={"bodega_id": str(bodega.id), "nombre": bodega.nombre, "activa": bodega.activa},
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return bodega

    @classmethod
    @transaction.atomic
    def actualizar_bodega(cls, *, bodega_id, empresa, usuario, data):
        """Actualiza una bodega registrando solo cambios efectivos del maestro."""
        bodega = cls._get_bodega_for_update(bodega_id=bodega_id, empresa=empresa)
        before = cls._snapshot(bodega)

        for field, value in data.items():
            setattr(bodega, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(bodega))
        if not planned_changes:
            return bodega

        cls._save_instance(bodega, "Ya existe una bodega con el mismo nombre en la empresa activa.")
        after = cls._snapshot(bodega)
        changes = cls._build_changes(before, after)
        if not changes:
            return bodega

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_id=bodega.id,
            event_name="inventario.bodega.actualizada",
            action_code=Acciones.EDITAR,
            summary=f"Bodega {bodega.nombre} actualizada.",
            payload={"bodega_id": str(bodega.id), "nombre": bodega.nombre, "activa": bodega.activa},
            changes=changes,
        )
        return bodega

    @classmethod
    @transaction.atomic
    def eliminar_bodega(cls, *, bodega_id, empresa, usuario):
        """Elimina una bodega sin uso o la inactiva si mantiene referencias historicas."""
        bodega = cls._get_bodega_for_update(bodega_id=bodega_id, empresa=empresa)
        before = cls._snapshot(bodega)
        bodega_pk = bodega.id
        bodega_nombre = bodega.nombre

        if cls._tiene_referencias_historicas(bodega):
            if not bodega.activa:
                raise ConflictError("La bodega ya esta inactiva y mantiene referencias historicas.")

            bodega.activa = False
            cls._save_instance(bodega, "No se pudo inactivar la bodega.", skip_clean=True, update_fields=["activa"])
            after = cls._snapshot(bodega)
            changes = cls._build_changes(before, after)
            cls._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                aggregate_id=bodega.id,
                event_name="inventario.bodega.inactivada",
                action_code=Acciones.BORRAR,
                summary=f"Bodega {bodega.nombre} inactivada por uso historico.",
                payload={
                    "bodega_id": str(bodega.id),
                    "nombre": bodega.nombre,
                    "activa": bodega.activa,
                    "deleted": False,
                },
                changes=changes,
            )
            return {"deleted": False, "bodega": bodega}

        bodega.delete()
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_id=bodega_pk,
            event_name="inventario.bodega.eliminada",
            action_code=Acciones.BORRAR,
            summary=f"Bodega {bodega_nombre} eliminada.",
            payload={"bodega_id": str(bodega_pk), "nombre": bodega_nombre, "activa": False, "deleted": True},
            changes={field: [value, None] for field, value in before.items() if value is not None},
        )
        return {"deleted": True, "bodega": None}
