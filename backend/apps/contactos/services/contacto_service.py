import django.core.exceptions as django_exceptions
from django.db import IntegrityError, transaction

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.contactos.models import Cliente, Contacto, CuentaBancaria, Direccion, Proveedor
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.core.validators import formatear_rut


class _ContactosBaseService:
    """Utilidades compartidas para operaciones transaccionales del maestro de contactos."""

    module_code = Modulos.CONTACTOS
    source = "contactos.contacto_service"

    @staticmethod
    def _serialize_value(value):
        """Normaliza valores del agregado para auditoria y eventos sin ambiguedad de tipos."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def _snapshot(cls, instance, fields):
        """Construye una fotografia plana del agregado usando campos relevantes del negocio."""
        return {
            field: cls._serialize_value(getattr(instance, field))
            for field in fields
        }

    @staticmethod
    def _build_changes(before, after, fields):
        """Genera diff before/after solo para atributos con cambios efectivos."""
        changes = {}
        for field in fields:
            before_value = before.get(field)
            after_value = after.get(field)
            if before_value != after_value:
                changes[field] = [before_value, after_value]
        return changes

    @staticmethod
    def _translate_validation_error(exc):
        """Convierte ValidationError tecnico al contrato AppError del modulo."""
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "messages"):
            detail = exc.messages
        else:
            detail = str(exc)
        return BusinessRuleError(detail, error_code="VALIDATION_ERROR")

    @classmethod
    def _save_instance(cls, instance, conflict_message, **kwargs):
        """Persiste un agregado traduciendo validaciones e integridad a AppError."""
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
        severity=AuditSeverity.INFO,
        topic="contactos.catalogo",
    ):
        """Registra domain event, outbox y auditoria del modulo de contactos."""
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
            severity=severity,
            changes=changes or {},
            payload=payload,
            source=cls.source,
        )


class ContactoService(_ContactosBaseService):
    """Servicio de aplicacion para administrar contactos maestros del ERP."""

    audit_fields = (
        "nombre",
        "razon_social",
        "rut",
        "tipo",
        "email",
        "telefono",
        "celular",
        "activo",
        "notas",
    )

    @staticmethod
    def _get_contacto_for_update(*, contacto_id, empresa):
        """Obtiene el contacto con lock pesimista para cambios concurrentes del maestro."""
        contacto = Contacto.all_objects.select_for_update().filter(id=contacto_id, empresa=empresa).first()
        if not contacto:
            raise ResourceNotFoundError("Contacto no encontrado.")
        return contacto

    @staticmethod
    def _find_contacto_by_rut_for_update(*, empresa, rut):
        """Busca un contacto existente por RUT normalizado para reutilizar o reactivar altas repetidas."""
        normalized_rut = formatear_rut(rut)
        if not str(normalized_rut or "").strip():
            return None
        return (
            Contacto.all_objects.select_for_update()
            .filter(empresa=empresa, rut=normalized_rut)
            .first()
        )

    @classmethod
    @transaction.atomic
    def crear_contacto(cls, *, empresa, usuario, data):
        """Crea un contacto maestro o reutiliza uno existente por RUT dentro de la misma empresa."""
        existing_contacto = cls._find_contacto_by_rut_for_update(empresa=empresa, rut=data.get("rut"))
        if existing_contacto:
            before = cls._snapshot(existing_contacto, cls.audit_fields)
            was_inactive = not existing_contacto.activo

            for field, value in data.items():
                setattr(existing_contacto, field, value)

            planned_changes = cls._build_changes(
                before,
                cls._snapshot(existing_contacto, cls.audit_fields),
                cls.audit_fields,
            )
            if not planned_changes:
                return existing_contacto

            cls._save_instance(existing_contacto, "Ya existe un contacto con el mismo RUT en la empresa activa.")
            after = cls._snapshot(existing_contacto, cls.audit_fields)
            changes = cls._build_changes(before, after, cls.audit_fields)
            if changes:
                payload = {
                    "contacto_id": str(existing_contacto.id),
                    "nombre": existing_contacto.nombre,
                    "rut": existing_contacto.rut,
                    "tipo": existing_contacto.tipo,
                    "activo": existing_contacto.activo,
                    "reused_existing": True,
                    "reactivated": was_inactive and existing_contacto.activo,
                    "changed_fields": sorted(changes.keys()),
                }
                cls._record_side_effects(
                    empresa=empresa,
                    usuario=usuario,
                    aggregate_type="Contacto",
                    aggregate_id=existing_contacto.id,
                    event_name="contacto.actualizado",
                    action_code=Acciones.EDITAR,
                    entity_type="CONTACTO",
                    summary=f"Contacto {existing_contacto.nombre} reutilizado desde alta por RUT existente.",
                    payload=payload,
                    changes=changes,
                )
            return existing_contacto

        contacto = Contacto(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(contacto, "Ya existe un contacto con el mismo RUT en la empresa activa.")

        snapshot = cls._snapshot(contacto, cls.audit_fields)
        payload = {
            "contacto_id": str(contacto.id),
            "nombre": contacto.nombre,
            "rut": contacto.rut,
            "tipo": contacto.tipo,
            "activo": contacto.activo,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Contacto",
            aggregate_id=contacto.id,
            event_name="contacto.creado",
            action_code=Acciones.CREAR,
            entity_type="CONTACTO",
            summary=f"Contacto {contacto.nombre} creado.",
            payload=payload,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return contacto

    @classmethod
    @transaction.atomic
    def actualizar_contacto(cls, *, contacto_id, empresa, usuario, data):
        """Actualiza un contacto existente registrando solo cambios efectivos."""
        contacto = cls._get_contacto_for_update(contacto_id=contacto_id, empresa=empresa)
        before = cls._snapshot(contacto, cls.audit_fields)

        for field, value in data.items():
            setattr(contacto, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(contacto, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return contacto

        cls._save_instance(contacto, "Ya existe un contacto con el mismo RUT en la empresa activa.")
        after = cls._snapshot(contacto, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return contacto

        payload = {
            "contacto_id": str(contacto.id),
            "nombre": contacto.nombre,
            "rut": contacto.rut,
            "tipo": contacto.tipo,
            "activo": contacto.activo,
            "changed_fields": sorted(changes.keys()),
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Contacto",
            aggregate_id=contacto.id,
            event_name="contacto.actualizado",
            action_code=Acciones.EDITAR,
            entity_type="CONTACTO",
            summary=f"Contacto {contacto.nombre} actualizado.",
            payload=payload,
            changes=changes,
        )
        return contacto

    @classmethod
    @transaction.atomic
    def eliminar_contacto(cls, *, contacto_id, empresa, usuario):
        """Elimina un contacto si no mantiene relacion comercial activa en el ERP."""
        contacto = cls._get_contacto_for_update(contacto_id=contacto_id, empresa=empresa)
        if Cliente.all_objects.filter(empresa=empresa, contacto=contacto).exists():
            raise ConflictError("No se puede eliminar el contacto porque aun esta asociado a un cliente.")
        if Proveedor.all_objects.filter(empresa=empresa, contacto=contacto).exists():
            raise ConflictError("No se puede eliminar el contacto porque aun esta asociado a un proveedor.")

        before = cls._snapshot(contacto, cls.audit_fields)
        contacto_id_value = contacto.id
        contacto_nombre = contacto.nombre
        contacto.delete()

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Contacto",
            aggregate_id=contacto_id_value,
            event_name="contacto.eliminado",
            action_code=Acciones.BORRAR,
            entity_type="CONTACTO",
            summary=f"Contacto {contacto_nombre} eliminado.",
            payload={
                "contacto_id": str(contacto_id_value),
                "nombre": contacto_nombre,
                "deleted": True,
            },
            changes={field: [value, None] for field, value in before.items() if value is not None},
            severity=AuditSeverity.WARNING,
        )
        return {"deleted": True}


class ClienteService(_ContactosBaseService):
    """Servicio de aplicacion para administrar la ficha comercial de clientes."""

    contacto_fields = ("nombre", "razon_social", "rut", "tipo", "email", "telefono", "celular", "notas", "activo")
    audit_fields = ("contacto_id", "limite_credito", "dias_credito", "categoria_cliente", "segmento")

    @staticmethod
    def _get_cliente_for_update(*, cliente_id, empresa):
        """Obtiene el cliente con lock pesimista para cambios concurrentes de la ficha comercial."""
        cliente = (
            Cliente.all_objects.select_for_update()
            .select_related("contacto")
            .filter(id=cliente_id, empresa=empresa)
            .first()
        )
        if not cliente:
            raise ResourceNotFoundError("Cliente no encontrado.")
        return cliente

    @classmethod
    @transaction.atomic
    def crear_cliente(cls, *, empresa, usuario, data):
        """Crea una ficha de cliente y registra trazabilidad funcional consistente."""
        cliente = Cliente(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(cliente, "El contacto ya tiene una ficha de cliente en la empresa activa.")

        snapshot = cls._snapshot(cliente, cls.audit_fields)
        payload = {
            "cliente_id": str(cliente.id),
            "contacto_id": str(cliente.contacto_id),
            "contacto_nombre": cliente.contacto.nombre,
            "limite_credito": str(cliente.limite_credito),
            "dias_credito": cliente.dias_credito,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Cliente",
            aggregate_id=cliente.id,
            event_name="cliente.creado",
            action_code=Acciones.CREAR,
            entity_type="CLIENTE",
            summary=f"Cliente {cliente.contacto.nombre} creado.",
            payload=payload,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return cliente

    @classmethod
    @transaction.atomic
    def crear_cliente_con_contacto(cls, *, empresa, usuario, data):
        """Crea un cliente resolviendo alta o reutilizacion del contacto maestro en una sola operacion."""
        contacto_data = {field: data.get(field) for field in cls.contacto_fields if field in data}
        cliente_data = {
            "limite_credito": data.get("limite_credito"),
            "dias_credito": data.get("dias_credito"),
            "categoria_cliente": data.get("categoria_cliente"),
            "segmento": data.get("segmento"),
        }
        contacto = ContactoService.crear_contacto(empresa=empresa, usuario=usuario, data=contacto_data)
        cliente_data["contacto"] = contacto
        return cls.crear_cliente(empresa=empresa, usuario=usuario, data=cliente_data)

    @classmethod
    @transaction.atomic
    def actualizar_cliente(cls, *, cliente_id, empresa, usuario, data):
        """Actualiza la ficha comercial de cliente emitiendo solo cambios efectivos."""
        cliente = cls._get_cliente_for_update(cliente_id=cliente_id, empresa=empresa)
        before = cls._snapshot(cliente, cls.audit_fields)

        for field, value in data.items():
            setattr(cliente, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(cliente, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return cliente

        cls._save_instance(cliente, "El contacto ya tiene una ficha de cliente en la empresa activa.")
        after = cls._snapshot(cliente, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return cliente

        payload = {
            "cliente_id": str(cliente.id),
            "contacto_id": str(cliente.contacto_id),
            "contacto_nombre": cliente.contacto.nombre,
            "changed_fields": sorted(changes.keys()),
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Cliente",
            aggregate_id=cliente.id,
            event_name="cliente.actualizado",
            action_code=Acciones.EDITAR,
            entity_type="CLIENTE",
            summary=f"Cliente {cliente.contacto.nombre} actualizado.",
            payload=payload,
            changes=changes,
        )
        return cliente

    @classmethod
    @transaction.atomic
    def actualizar_cliente_con_contacto(cls, *, cliente_id, empresa, usuario, data):
        """Actualiza en una sola transaccion la ficha de cliente y su contacto maestro asociado."""
        cliente = cls._get_cliente_for_update(cliente_id=cliente_id, empresa=empresa)

        contacto_data = {field: data.get(field) for field in cls.contacto_fields if field in data}
        cliente_data = {
            "limite_credito": data.get("limite_credito"),
            "dias_credito": data.get("dias_credito"),
            "categoria_cliente": data.get("categoria_cliente"),
            "segmento": data.get("segmento"),
        }

        if contacto_data:
            ContactoService.actualizar_contacto(
                contacto_id=cliente.contacto_id,
                empresa=empresa,
                usuario=usuario,
                data=contacto_data,
            )

        cliente_data = {key: value for key, value in cliente_data.items() if key in data}
        if cliente_data:
            cliente = cls.actualizar_cliente(
                cliente_id=cliente_id,
                empresa=empresa,
                usuario=usuario,
                data=cliente_data,
            )

        return cliente

    @classmethod
    @transaction.atomic
    def eliminar_cliente(cls, *, cliente_id, empresa, usuario):
        """Elimina la ficha comercial y borra el contacto si queda sin relacion comercial."""
        cliente = cls._get_cliente_for_update(cliente_id=cliente_id, empresa=empresa)
        contacto = Contacto.all_objects.select_for_update().filter(id=cliente.contacto_id, empresa=empresa).first()
        before = cls._snapshot(cliente, cls.audit_fields)
        cliente_id_value = cliente.id
        contacto_id_value = cliente.contacto_id
        contacto_nombre = cliente.contacto.nombre

        cliente.delete()

        payload = {
            "cliente_id": str(cliente_id_value),
            "contacto_id": str(contacto_id_value),
            "contacto_nombre": contacto_nombre,
        }
        deleted_contact = False
        if contacto and not Proveedor.all_objects.filter(empresa=empresa, contacto_id=contacto_id_value).exists():
            contacto.delete()
            deleted_contact = True

        payload["deleted_contact"] = deleted_contact
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Cliente",
            aggregate_id=cliente_id_value,
            event_name="cliente.eliminado",
            action_code=Acciones.BORRAR,
            entity_type="CLIENTE",
            summary=f"Cliente {contacto_nombre} eliminado.",
            payload=payload,
            changes={field: [value, None] for field, value in before.items() if value is not None},
            severity=AuditSeverity.WARNING,
        )

        if deleted_contact:
            ContactoService._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                aggregate_type="Contacto",
                aggregate_id=contacto_id_value,
                event_name="contacto.eliminado",
                action_code=Acciones.BORRAR,
                entity_type="CONTACTO",
                summary=f"Contacto {contacto_nombre} eliminado por quedar sin relacion comercial.",
                payload={
                    "contacto_id": str(contacto_id_value),
                    "nombre": contacto_nombre,
                    "origin": "cliente.eliminado",
                },
                changes={
                    "deleted_by_cascade": [False, True],
                },
                severity=AuditSeverity.WARNING,
            )

        return {"deleted": True, "deleted_contact": deleted_contact}


class ProveedorService(_ContactosBaseService):
    """Servicio de aplicacion para administrar la ficha de proveedores del ERP."""

    contacto_fields = ("nombre", "razon_social", "rut", "tipo", "email", "telefono", "celular", "notas", "activo")
    audit_fields = ("contacto_id", "giro", "vendedor_contacto", "dias_credito")

    @staticmethod
    def _get_proveedor_for_update(*, proveedor_id, empresa):
        """Obtiene el proveedor con lock pesimista para cambios concurrentes de la ficha."""
        proveedor = (
            Proveedor.all_objects.select_for_update()
            .select_related("contacto")
            .filter(id=proveedor_id, empresa=empresa)
            .first()
        )
        if not proveedor:
            raise ResourceNotFoundError("Proveedor no encontrado.")
        return proveedor

    @classmethod
    @transaction.atomic
    def crear_proveedor(cls, *, empresa, usuario, data):
        """Crea una ficha de proveedor con auditoria y eventos del agregado."""
        proveedor = Proveedor(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(proveedor, "El contacto ya tiene una ficha de proveedor en la empresa activa.")

        snapshot = cls._snapshot(proveedor, cls.audit_fields)
        payload = {
            "proveedor_id": str(proveedor.id),
            "contacto_id": str(proveedor.contacto_id),
            "contacto_nombre": proveedor.contacto.nombre,
            "giro": proveedor.giro,
            "dias_credito": proveedor.dias_credito,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Proveedor",
            aggregate_id=proveedor.id,
            event_name="proveedor.creado",
            action_code=Acciones.CREAR,
            entity_type="PROVEEDOR",
            summary=f"Proveedor {proveedor.contacto.nombre} creado.",
            payload=payload,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return proveedor

    @classmethod
    @transaction.atomic
    def crear_proveedor_con_contacto(cls, *, empresa, usuario, data):
        """Crea un proveedor resolviendo el contacto maestro dentro de la misma transaccion funcional."""
        contacto_data = {field: data.get(field) for field in cls.contacto_fields if field in data}
        proveedor_data = {
            "giro": data.get("giro"),
            "vendedor_contacto": data.get("vendedor_contacto"),
            "dias_credito": data.get("dias_credito"),
        }
        contacto = ContactoService.crear_contacto(empresa=empresa, usuario=usuario, data=contacto_data)
        proveedor_data["contacto"] = contacto
        return cls.crear_proveedor(empresa=empresa, usuario=usuario, data=proveedor_data)

    @classmethod
    @transaction.atomic
    def actualizar_proveedor(cls, *, proveedor_id, empresa, usuario, data):
        """Actualiza la ficha del proveedor registrando solo cambios efectivos."""
        proveedor = cls._get_proveedor_for_update(proveedor_id=proveedor_id, empresa=empresa)
        before = cls._snapshot(proveedor, cls.audit_fields)

        for field, value in data.items():
            setattr(proveedor, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(proveedor, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return proveedor

        cls._save_instance(proveedor, "El contacto ya tiene una ficha de proveedor en la empresa activa.")
        after = cls._snapshot(proveedor, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return proveedor

        payload = {
            "proveedor_id": str(proveedor.id),
            "contacto_id": str(proveedor.contacto_id),
            "contacto_nombre": proveedor.contacto.nombre,
            "changed_fields": sorted(changes.keys()),
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Proveedor",
            aggregate_id=proveedor.id,
            event_name="proveedor.actualizado",
            action_code=Acciones.EDITAR,
            entity_type="PROVEEDOR",
            summary=f"Proveedor {proveedor.contacto.nombre} actualizado.",
            payload=payload,
            changes=changes,
        )
        return proveedor

    @classmethod
    @transaction.atomic
    def actualizar_proveedor_con_contacto(cls, *, proveedor_id, empresa, usuario, data):
        """Actualiza en una sola transaccion la ficha de proveedor y su contacto maestro asociado."""
        proveedor = cls._get_proveedor_for_update(proveedor_id=proveedor_id, empresa=empresa)

        contacto_data = {field: data.get(field) for field in cls.contacto_fields if field in data}
        proveedor_data = {
            "giro": data.get("giro"),
            "vendedor_contacto": data.get("vendedor_contacto"),
            "dias_credito": data.get("dias_credito"),
        }

        if contacto_data:
            ContactoService.actualizar_contacto(
                contacto_id=proveedor.contacto_id,
                empresa=empresa,
                usuario=usuario,
                data=contacto_data,
            )

        proveedor_data = {key: value for key, value in proveedor_data.items() if key in data}
        if proveedor_data:
            proveedor = cls.actualizar_proveedor(
                proveedor_id=proveedor_id,
                empresa=empresa,
                usuario=usuario,
                data=proveedor_data,
            )

        return proveedor

    @classmethod
    @transaction.atomic
    def eliminar_proveedor(cls, *, proveedor_id, empresa, usuario):
        """Elimina la ficha del proveedor y limpia el contacto si queda sin relacion comercial."""
        proveedor = cls._get_proveedor_for_update(proveedor_id=proveedor_id, empresa=empresa)
        contacto = Contacto.all_objects.select_for_update().filter(id=proveedor.contacto_id, empresa=empresa).first()
        before = cls._snapshot(proveedor, cls.audit_fields)
        proveedor_id_value = proveedor.id
        contacto_id_value = proveedor.contacto_id
        contacto_nombre = proveedor.contacto.nombre

        proveedor.delete()

        payload = {
            "proveedor_id": str(proveedor_id_value),
            "contacto_id": str(contacto_id_value),
            "contacto_nombre": contacto_nombre,
        }
        deleted_contact = False
        if contacto and not Cliente.all_objects.filter(empresa=empresa, contacto_id=contacto_id_value).exists():
            contacto.delete()
            deleted_contact = True

        payload["deleted_contact"] = deleted_contact
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Proveedor",
            aggregate_id=proveedor_id_value,
            event_name="proveedor.eliminado",
            action_code=Acciones.BORRAR,
            entity_type="PROVEEDOR",
            summary=f"Proveedor {contacto_nombre} eliminado.",
            payload=payload,
            changes={field: [value, None] for field, value in before.items() if value is not None},
            severity=AuditSeverity.WARNING,
        )

        if deleted_contact:
            ContactoService._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                aggregate_type="Contacto",
                aggregate_id=contacto_id_value,
                event_name="contacto.eliminado",
                action_code=Acciones.BORRAR,
                entity_type="CONTACTO",
                summary=f"Contacto {contacto_nombre} eliminado por quedar sin relacion comercial.",
                payload={
                    "contacto_id": str(contacto_id_value),
                    "nombre": contacto_nombre,
                    "origin": "proveedor.eliminado",
                },
                changes={
                    "deleted_by_cascade": [False, True],
                },
                severity=AuditSeverity.WARNING,
            )

        return {"deleted": True, "deleted_contact": deleted_contact}


class DireccionService(_ContactosBaseService):
    """Servicio de aplicacion para administrar direcciones del tercero con trazabilidad funcional."""

    audit_fields = ("contacto_id", "tipo", "direccion", "comuna", "ciudad", "region", "pais")

    @staticmethod
    def _get_direccion_for_update(*, direccion_id, empresa):
        """Obtiene la direccion con lock pesimista para cambios concurrentes del maestro."""
        direccion = (
            Direccion.objects.select_for_update()
            .select_related("contacto")
            .filter(id=direccion_id, empresa=empresa)
            .first()
        )
        if not direccion:
            raise ResourceNotFoundError("Direccion no encontrada.")
        return direccion

    @classmethod
    @transaction.atomic
    def crear_direccion(cls, *, empresa, usuario, data):
        """Crea una direccion del tercero registrando auditoria, outbox y evento de dominio."""
        direccion = Direccion(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(direccion, "Ya existe una direccion del mismo tipo para este contacto.")

        snapshot = cls._snapshot(direccion, cls.audit_fields)
        payload = {
            "direccion_id": str(direccion.id),
            "contacto_id": str(direccion.contacto_id),
            "contacto_nombre": direccion.contacto.nombre,
            "tipo": direccion.tipo,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Direccion",
            aggregate_id=direccion.id,
            event_name="direccion.creada",
            action_code=Acciones.CREAR,
            entity_type="DIRECCION",
            summary=f"Direccion {direccion.tipo} creada para {direccion.contacto.nombre}.",
            payload=payload,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
            topic="contactos.relaciones",
        )
        return direccion

    @classmethod
    @transaction.atomic
    def actualizar_direccion(cls, *, direccion_id, empresa, usuario, data):
        """Actualiza una direccion existente registrando solo cambios efectivos del agregado."""
        direccion = cls._get_direccion_for_update(direccion_id=direccion_id, empresa=empresa)
        before = cls._snapshot(direccion, cls.audit_fields)

        for field, value in data.items():
            setattr(direccion, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(direccion, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return direccion

        cls._save_instance(direccion, "Ya existe una direccion del mismo tipo para este contacto.")
        after = cls._snapshot(direccion, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return direccion

        payload = {
            "direccion_id": str(direccion.id),
            "contacto_id": str(direccion.contacto_id),
            "contacto_nombre": direccion.contacto.nombre,
            "tipo": direccion.tipo,
            "changed_fields": sorted(changes.keys()),
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Direccion",
            aggregate_id=direccion.id,
            event_name="direccion.actualizada",
            action_code=Acciones.EDITAR,
            entity_type="DIRECCION",
            summary=f"Direccion {direccion.tipo} actualizada para {direccion.contacto.nombre}.",
            payload=payload,
            changes=changes,
            topic="contactos.relaciones",
        )
        return direccion

    @classmethod
    @transaction.atomic
    def eliminar_direccion(cls, *, direccion_id, empresa, usuario):
        """Elimina una direccion del tercero y deja trazabilidad completa del borrado."""
        direccion = cls._get_direccion_for_update(direccion_id=direccion_id, empresa=empresa)
        before = cls._snapshot(direccion, cls.audit_fields)
        direccion_id_value = direccion.id
        contacto_id_value = direccion.contacto_id
        contacto_nombre = direccion.contacto.nombre
        direccion_tipo = direccion.tipo
        direccion.delete()

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="Direccion",
            aggregate_id=direccion_id_value,
            event_name="direccion.eliminada",
            action_code=Acciones.BORRAR,
            entity_type="DIRECCION",
            summary=f"Direccion {direccion_tipo} eliminada para {contacto_nombre}.",
            payload={
                "direccion_id": str(direccion_id_value),
                "contacto_id": str(contacto_id_value),
                "contacto_nombre": contacto_nombre,
                "tipo": direccion_tipo,
            },
            changes={field: [value, None] for field, value in before.items() if value is not None},
            severity=AuditSeverity.WARNING,
            topic="contactos.relaciones",
        )
        return {"deleted": True}


class CuentaBancariaService(_ContactosBaseService):
    """Servicio de aplicacion para administrar cuentas bancarias del tercero con alta trazabilidad."""

    audit_fields = (
        "contacto_id",
        "banco",
        "tipo_cuenta",
        "numero_cuenta",
        "titular",
        "rut_titular",
        "activa",
    )

    @staticmethod
    def _get_cuenta_for_update(*, cuenta_id, empresa):
        """Obtiene la cuenta bancaria con lock pesimista para cambios concurrentes del tercero."""
        cuenta = (
            CuentaBancaria.objects.select_for_update()
            .select_related("contacto")
            .filter(id=cuenta_id, empresa=empresa)
            .first()
        )
        if not cuenta:
            raise ResourceNotFoundError("Cuenta bancaria no encontrada.")
        return cuenta

    @classmethod
    @transaction.atomic
    def crear_cuenta(cls, *, empresa, usuario, data):
        """Crea una cuenta bancaria del tercero registrando auditoria, evento y outbox."""
        cuenta = CuentaBancaria(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(cuenta, "Ya existe una cuenta bancaria con el mismo numero para este contacto.")

        snapshot = cls._snapshot(cuenta, cls.audit_fields)
        payload = {
            "cuenta_bancaria_id": str(cuenta.id),
            "contacto_id": str(cuenta.contacto_id),
            "contacto_nombre": cuenta.contacto.nombre,
            "banco": cuenta.banco,
            "tipo_cuenta": cuenta.tipo_cuenta,
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="CuentaBancaria",
            aggregate_id=cuenta.id,
            event_name="cuenta_bancaria.creada",
            action_code=Acciones.CREAR,
            entity_type="CUENTA_BANCARIA",
            summary=f"Cuenta bancaria creada para {cuenta.contacto.nombre}.",
            payload=payload,
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
            topic="contactos.relaciones",
        )
        return cuenta

    @classmethod
    @transaction.atomic
    def actualizar_cuenta(cls, *, cuenta_id, empresa, usuario, data):
        """Actualiza una cuenta bancaria existente registrando solo cambios efectivos."""
        cuenta = cls._get_cuenta_for_update(cuenta_id=cuenta_id, empresa=empresa)
        before = cls._snapshot(cuenta, cls.audit_fields)

        for field, value in data.items():
            setattr(cuenta, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(cuenta, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return cuenta

        cls._save_instance(cuenta, "Ya existe una cuenta bancaria con el mismo numero para este contacto.")
        after = cls._snapshot(cuenta, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return cuenta

        payload = {
            "cuenta_bancaria_id": str(cuenta.id),
            "contacto_id": str(cuenta.contacto_id),
            "contacto_nombre": cuenta.contacto.nombre,
            "banco": cuenta.banco,
            "tipo_cuenta": cuenta.tipo_cuenta,
            "changed_fields": sorted(changes.keys()),
        }
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="CuentaBancaria",
            aggregate_id=cuenta.id,
            event_name="cuenta_bancaria.actualizada",
            action_code=Acciones.EDITAR,
            entity_type="CUENTA_BANCARIA",
            summary=f"Cuenta bancaria actualizada para {cuenta.contacto.nombre}.",
            payload=payload,
            changes=changes,
            topic="contactos.relaciones",
        )
        return cuenta

    @classmethod
    @transaction.atomic
    def eliminar_cuenta(cls, *, cuenta_id, empresa, usuario):
        """Elimina una cuenta bancaria del tercero y deja trazabilidad funcional del borrado."""
        cuenta = cls._get_cuenta_for_update(cuenta_id=cuenta_id, empresa=empresa)
        before = cls._snapshot(cuenta, cls.audit_fields)
        cuenta_id_value = cuenta.id
        contacto_id_value = cuenta.contacto_id
        contacto_nombre = cuenta.contacto.nombre
        banco = cuenta.banco
        cuenta.delete()

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="CuentaBancaria",
            aggregate_id=cuenta_id_value,
            event_name="cuenta_bancaria.eliminada",
            action_code=Acciones.BORRAR,
            entity_type="CUENTA_BANCARIA",
            summary=f"Cuenta bancaria eliminada para {contacto_nombre}.",
            payload={
                "cuenta_bancaria_id": str(cuenta_id_value),
                "contacto_id": str(contacto_id_value),
                "contacto_nombre": contacto_nombre,
                "banco": banco,
            },
            changes={field: [value, None] for field, value in before.items() if value is not None},
            severity=AuditSeverity.WARNING,
            topic="contactos.relaciones",
        )
        return {"deleted": True}
