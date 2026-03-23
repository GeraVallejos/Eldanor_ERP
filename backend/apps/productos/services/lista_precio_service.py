import django.core.exceptions as django_exceptions
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.productos.models import ListaPrecio, ListaPrecioItem


class _ListaPrecioBaseService:
    """Utilidades compartidas para servicios comerciales de listas de precio."""

    source = "productos.lista_precio_service"

    @staticmethod
    def _serialize_value(value):
        """Normaliza valores a una forma estable para cambios y payloads."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def _snapshot(cls, instance, fields):
        """Obtiene una fotografia plana de los campos funcionales del agregado."""
        return {field: cls._serialize_value(getattr(instance, field)) for field in fields}

    @staticmethod
    def _build_changes(before, after, fields):
        """Construye un diff limitado a campos efectivamente modificados."""
        changes = {}
        for field in fields:
            before_value = before.get(field)
            after_value = after.get(field)
            if before_value != after_value:
                changes[field] = [before_value, after_value]
        return changes

    @staticmethod
    def _translate_validation_error(exc):
        """Traduce ValidationError de Django al contrato AppError."""
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "messages"):
            detail = exc.messages
        else:
            detail = str(exc)
        return BusinessRuleError(detail, error_code="VALIDATION_ERROR")

    @classmethod
    def _save_instance(cls, instance, conflict_message, **kwargs):
        """Persiste el agregado comercial traduciendo integridad y validacion."""
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
    ):
        """Registra eventos, outbox y auditoria para configuracion comercial."""
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
            topic="productos.precios",
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
            entity_type=entity_type,
            entity_id=aggregate_id,
            summary=summary,
            severity=AuditSeverity.INFO,
            changes=changes or {},
            payload=payload,
            source=cls.source,
        )


class ListaPrecioService(_ListaPrecioBaseService):
    """Servicio de aplicacion para administrar listas de precio comerciales."""

    audit_fields = ("nombre", "moneda_id", "cliente_id", "fecha_desde", "fecha_hasta", "activa", "prioridad")

    @classmethod
    def _validate_overlapping_scope(cls, *, empresa, lista, exclude_id=None):
        """Evita listas activas superpuestas con el mismo alcance y prioridad comercial."""
        if not lista.activa:
            return

        overlap_queryset = ListaPrecio.all_objects.filter(
            empresa=empresa,
            activa=True,
            cliente_id=lista.cliente_id,
            prioridad=lista.prioridad,
        )

        if exclude_id:
            overlap_queryset = overlap_queryset.exclude(id=exclude_id)

        overlap_queryset = overlap_queryset.filter(
            Q(fecha_hasta__isnull=True) | Q(fecha_hasta__gte=lista.fecha_desde)
        )
        if lista.fecha_hasta is not None:
            overlap_queryset = overlap_queryset.filter(fecha_desde__lte=lista.fecha_hasta)

        conflicto = overlap_queryset.order_by("fecha_desde", "creado_en").first()
        if not conflicto:
            return

        alcance = "general" if lista.cliente_id is None else "del cliente seleccionado"
        raise ConflictError(
            "Ya existe una lista de precio activa y superpuesta para el mismo alcance y prioridad.",
            meta={
                "source": cls.source,
                "conflicting_list_id": str(conflicto.id),
                "scope": alcance,
            },
        )

    @staticmethod
    def _get_lista_for_update(*, lista_id, empresa):
        """Obtiene la lista con lock para cambios concurrentes de configuracion comercial."""
        lista = ListaPrecio.all_objects.select_for_update().filter(id=lista_id, empresa=empresa).first()
        if not lista:
            raise ResourceNotFoundError("Lista de precio no encontrada.")
        return lista

    @classmethod
    @transaction.atomic
    def crear_lista(cls, *, empresa, usuario, data):
        """Crea una lista de precio con trazabilidad funcional completa."""
        lista = ListaPrecio(empresa=empresa, creado_por=usuario, **data)
        cls._validate_overlapping_scope(empresa=empresa, lista=lista)
        cls._save_instance(lista, "Ya existe una lista de precio en conflicto con la configuracion indicada.")

        snapshot = cls._snapshot(lista, cls.audit_fields)
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ListaPrecio",
            aggregate_id=lista.id,
            event_name="lista_precio.creada",
            action_code=Acciones.CREAR,
            entity_type="LISTA_PRECIO",
            summary=f"Lista de precio {lista.nombre} creada.",
            payload={
                "lista_id": str(lista.id),
                "nombre": lista.nombre,
                "cliente_id": str(lista.cliente_id) if lista.cliente_id else None,
                "moneda_id": str(lista.moneda_id),
                "activa": lista.activa,
                "prioridad": lista.prioridad,
            },
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return lista

    @classmethod
    @transaction.atomic
    def actualizar_lista(cls, *, lista_id, empresa, usuario, data):
        """Actualiza una lista de precio preservando trazabilidad de cambios comerciales."""
        lista = cls._get_lista_for_update(lista_id=lista_id, empresa=empresa)
        before = cls._snapshot(lista, cls.audit_fields)

        for field, value in data.items():
            setattr(lista, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(lista, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return lista

        cls._validate_overlapping_scope(empresa=empresa, lista=lista, exclude_id=lista.id)
        cls._save_instance(lista, "Ya existe una lista de precio en conflicto con la configuracion indicada.")
        after = cls._snapshot(lista, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return lista

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ListaPrecio",
            aggregate_id=lista.id,
            event_name="lista_precio.actualizada",
            action_code=Acciones.EDITAR,
            entity_type="LISTA_PRECIO",
            summary=f"Lista de precio {lista.nombre} actualizada.",
            payload={
                "lista_id": str(lista.id),
                "nombre": lista.nombre,
                "cliente_id": str(lista.cliente_id) if lista.cliente_id else None,
                "moneda_id": str(lista.moneda_id),
                "activa": lista.activa,
                "prioridad": lista.prioridad,
            },
            changes=changes,
        )
        return lista

    @classmethod
    @transaction.atomic
    def eliminar_lista(cls, *, lista_id, empresa, usuario):
        """Elimina o desactiva una lista de precio segun sus referencias historicas."""
        lista = cls._get_lista_for_update(lista_id=lista_id, empresa=empresa)
        before = cls._snapshot(lista, cls.audit_fields)
        lista_pk = lista.id

        try:
            lista.delete()
        except ProtectedError as exc:
            if not lista.activa:
                raise ConflictError("La lista ya esta inactiva y mantiene referencias historicas.") from exc

            lista.activa = False
            cls._save_instance(lista, "No se pudo desactivar la lista.", skip_clean=True, update_fields=["activa"])
            after = cls._snapshot(lista, cls.audit_fields)
            changes = cls._build_changes(before, after, cls.audit_fields)
            cls._record_side_effects(
                empresa=empresa,
                usuario=usuario,
                aggregate_type="ListaPrecio",
                aggregate_id=lista.id,
                event_name="lista_precio.desactivada",
                action_code=Acciones.BORRAR,
                entity_type="LISTA_PRECIO",
                summary=f"Lista de precio {lista.nombre} desactivada.",
                payload={
                    "lista_id": str(lista.id),
                    "nombre": lista.nombre,
                    "cliente_id": str(lista.cliente_id) if lista.cliente_id else None,
                    "moneda_id": str(lista.moneda_id),
                    "activa": lista.activa,
                    "prioridad": lista.prioridad,
                },
                changes=changes,
            )
            return {"deleted": False, "lista": lista}

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ListaPrecio",
            aggregate_id=lista_pk,
            event_name="lista_precio.eliminada",
            action_code=Acciones.BORRAR,
            entity_type="LISTA_PRECIO",
            summary=f"Lista de precio {before.get('nombre')} eliminada.",
            payload={
                "lista_id": str(lista_pk),
                "nombre": before.get("nombre"),
                "cliente_id": before.get("cliente_id"),
                "moneda_id": before.get("moneda_id"),
                "activa": False,
                "prioridad": before.get("prioridad"),
            },
            changes={field: [value, None] for field, value in before.items() if value is not None},
        )
        return {"deleted": True, "lista": None}


class ListaPrecioItemService(_ListaPrecioBaseService):
    """Servicio de aplicacion para items de listas de precio por producto."""

    audit_fields = ("lista_id", "producto_id", "precio", "descuento_maximo")

    @staticmethod
    def _get_item_for_update(*, item_id, empresa):
        """Obtiene el item con lock para modificaciones concurrentes del precio comercial."""
        item = (
            ListaPrecioItem.all_objects
            .select_for_update()
            .select_related("lista", "producto")
            .filter(id=item_id, empresa=empresa)
            .first()
        )
        if not item:
            raise ResourceNotFoundError("Item de lista de precio no encontrado.")
        return item

    @classmethod
    @transaction.atomic
    def crear_item(cls, *, empresa, usuario, data):
        """Crea un item comercial por producto dentro de una lista de precio."""
        item = ListaPrecioItem(empresa=empresa, creado_por=usuario, **data)
        cls._save_instance(item, "El producto ya existe en la lista de precio seleccionada.")

        snapshot = cls._snapshot(item, cls.audit_fields)
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ListaPrecioItem",
            aggregate_id=item.id,
            event_name="lista_precio_item.creado",
            action_code=Acciones.CREAR,
            entity_type="LISTA_PRECIO_ITEM",
            summary=f"Precio para producto {item.producto.nombre} agregado a lista {item.lista.nombre}.",
            payload={
                "item_id": str(item.id),
                "lista_id": str(item.lista_id),
                "producto_id": str(item.producto_id),
                "precio": str(item.precio),
                "descuento_maximo": str(item.descuento_maximo),
            },
            changes={field: [None, value] for field, value in snapshot.items() if value is not None},
        )
        return item

    @classmethod
    @transaction.atomic
    def actualizar_item(cls, *, item_id, empresa, usuario, data):
        """Actualiza un item comercial preservando la trazabilidad del precio configurado."""
        item = cls._get_item_for_update(item_id=item_id, empresa=empresa)
        before = cls._snapshot(item, cls.audit_fields)

        for field, value in data.items():
            setattr(item, field, value)

        planned_changes = cls._build_changes(before, cls._snapshot(item, cls.audit_fields), cls.audit_fields)
        if not planned_changes:
            return item

        cls._save_instance(item, "El producto ya existe en la lista de precio seleccionada.")
        after = cls._snapshot(item, cls.audit_fields)
        changes = cls._build_changes(before, after, cls.audit_fields)
        if not changes:
            return item

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ListaPrecioItem",
            aggregate_id=item.id,
            event_name="lista_precio_item.actualizado",
            action_code=Acciones.EDITAR,
            entity_type="LISTA_PRECIO_ITEM",
            summary=f"Precio para producto {item.producto.nombre} actualizado en lista {item.lista.nombre}.",
            payload={
                "item_id": str(item.id),
                "lista_id": str(item.lista_id),
                "producto_id": str(item.producto_id),
                "precio": str(item.precio),
                "descuento_maximo": str(item.descuento_maximo),
            },
            changes=changes,
        )
        return item

    @classmethod
    @transaction.atomic
    def eliminar_item(cls, *, item_id, empresa, usuario):
        """Elimina un item de lista preservando evidencia de configuracion removida."""
        item = cls._get_item_for_update(item_id=item_id, empresa=empresa)
        before = cls._snapshot(item, cls.audit_fields)
        item_pk = item.id
        lista_nombre = item.lista.nombre
        producto_nombre = item.producto.nombre

        try:
            item.delete()
        except ProtectedError as exc:
            raise ConflictError("No se pudo eliminar el item porque mantiene referencias protegidas.") from exc

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            aggregate_type="ListaPrecioItem",
            aggregate_id=item_pk,
            event_name="lista_precio_item.eliminado",
            action_code=Acciones.BORRAR,
            entity_type="LISTA_PRECIO_ITEM",
            summary=f"Precio para producto {producto_nombre} eliminado de lista {lista_nombre}.",
            payload={
                "item_id": str(item_pk),
                "lista_id": before.get("lista_id"),
                "producto_id": before.get("producto_id"),
                "precio": before.get("precio"),
                "descuento_maximo": before.get("descuento_maximo"),
            },
            changes={field: [value, None] for field, value in before.items() if value is not None},
        )
        return {"deleted": True}
