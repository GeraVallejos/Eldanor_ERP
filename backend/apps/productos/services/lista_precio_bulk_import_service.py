from decimal import Decimal, InvalidOperation

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import AuthorizationError, BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.roles import RolUsuario
from apps.core.services import DomainEventService, OutboxService, build_bulk_import_result, format_bulk_import_row_error
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.xlsx_template import build_xlsx_template
from apps.productos.models import ListaPrecio, ListaPrecioItem, Producto
from apps.productos.services.lista_precio_service import ListaPrecioItemService
from apps.productos.validators import normalize_sku


def _to_decimal(raw_value, *, default=Decimal("0")):
    """Convierte un valor tabular a decimal soportando coma o punto como separador."""
    value = str(raw_value or "").strip()
    if not value:
        return default

    normalized = value.replace(" ", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise BusinessRuleError("Valor numerico invalido.") from exc


def _ensure_admin_user(user, empresa):
    """Restringe la carga masiva a administradores de la empresa activa."""
    if getattr(user, "is_superuser", False):
        return

    if not empresa:
        raise AuthorizationError(
            "No hay empresa activa para esta operacion.",
            error_code="BULK_IMPORT_NO_EMPRESA",
        )

    rol = user.get_rol_en_empresa(empresa)
    if rol != RolUsuario.ADMIN:
        raise AuthorizationError(
            "Solo el administrador de la empresa puede ejecutar carga masiva.",
            error_code="BULK_IMPORT_ADMIN_ONLY",
        )


def _resolve_import_empresa(user, empresa):
    """Resuelve la empresa activa del usuario para procesos masivos multiempresa."""
    if empresa:
        return empresa

    user_empresa = getattr(user, "empresa_activa", None)
    if user_empresa:
        return user_empresa

    if hasattr(user, "empresas_rel"):
        relacion = user.empresas_rel.filter(activo=True).select_related("empresa").first()
        if relacion:
            return relacion.empresa

    raise BusinessRuleError(
        "No hay empresa activa para ejecutar la carga masiva.",
        error_code="BULK_IMPORT_NO_EMPRESA",
    )


def _get_lista_activa(*, lista_id, empresa):
    """Obtiene la lista seleccionada dentro de la empresa activa para aplicar la importacion."""
    lista = ListaPrecio.all_objects.filter(id=lista_id, empresa=empresa).first()
    if not lista:
        raise ResourceNotFoundError("Lista de precio no encontrada.")
    return lista


def _registrar_resumen_importacion(*, empresa, user, lista, payload):
    """Registra el cierre auditable de una carga masiva sobre una lista de precio."""
    dedup_suffix = f"{lista.id}:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}"
    DomainEventService.record_event(
        empresa=empresa,
        aggregate_type="ListaPrecioBulkImport",
        aggregate_id=lista.id,
        event_type="lista_precio.bulk_import.finalizado",
        payload=payload,
        meta={"source": "productos.lista_precio_bulk_import_service"},
        idempotency_key=f"lista-precio-bulk-import:{dedup_suffix}",
        usuario=user,
    )
    OutboxService.enqueue(
        empresa=empresa,
        topic="productos.precios",
        event_name="lista_precio.bulk_import.finalizado",
        payload=payload,
        usuario=user,
        dedup_key=f"lista-precio-bulk-import:{dedup_suffix}",
    )
    AuditoriaService.registrar_evento(
        empresa=empresa,
        usuario=user,
        module_code=Modulos.PRODUCTOS,
        action_code=Acciones.EDITAR,
        event_type="LISTA_PRECIO_BULK_IMPORT",
        entity_type="LISTA_PRECIO",
        entity_id=lista.id,
        summary=f"Carga masiva ejecutada sobre lista {lista.nombre}.",
        severity=AuditSeverity.INFO,
        changes={
            "registros_creados": [0, int(payload["created"])],
            "registros_actualizados": [0, int(payload["updated"])],
            "filas_con_error": [0, int(payload["errors"])],
        },
        payload=payload,
        source="productos.lista_precio_bulk_import_service",
        idempotency_key=f"audit:lista-precio-bulk-import:{dedup_suffix}",
    )


def _validar_item_preview(*, empresa, lista, producto, precio, descuento_maximo):
    """Valida una fila de importacion sin persistir cambios ni efectos laterales."""
    item = ListaPrecioItem(
        empresa=empresa,
        lista=lista,
        producto=producto,
        precio=precio,
        descuento_maximo=descuento_maximo,
    )
    item.full_clean(validate_unique=False, validate_constraints=False)


def _build_zero_price_warning(*, line_number, sku, producto_nombre):
    """Construye una advertencia no bloqueante para filas con precio igual a cero."""
    return {
        "code": "PRECIO_CERO",
        "line": line_number,
        "sku": sku,
        "detail": f"El producto {producto_nombre} se importara con precio 0 en la lista.",
    }


def _get_existing_item(*, empresa, lista, producto):
    """Obtiene un item existente por lista y producto para aplicar comportamiento upsert."""
    return (
        ListaPrecioItem.all_objects
        .select_related("lista", "producto")
        .filter(empresa=empresa, lista=lista, producto=producto)
        .first()
    )


def bulk_import_lista_precio_items(*, lista_id, uploaded_file, user, empresa, dry_run=False):
    """Importa o previsualiza precios por SKU sobre una lista existente."""
    empresa = _resolve_import_empresa(user, empresa)
    _ensure_admin_user(user, empresa)
    lista = _get_lista_activa(lista_id=lista_id, empresa=empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["sku", "precio"],
    )

    sku_candidates = []
    for _line, row in rows:
        sku_value = str(row.get("sku") or "").strip()
        if sku_value:
            sku_candidates.append(normalize_sku(sku_value))

    productos_by_sku = {
        producto.sku: producto
        for producto in Producto.all_objects.filter(empresa=empresa, sku__in=sku_candidates)
    }
    items_existentes = {
        item.producto_id: item
        for item in ListaPrecioItem.all_objects.select_related("producto").filter(empresa=empresa, lista=lista)
    }

    created = 0
    updated = 0
    errors = []
    warnings = []

    for line_number, row in rows:
        try:
            sku_raw = str(row.get("sku") or "").strip()
            if not sku_raw:
                raise BusinessRuleError("El SKU es obligatorio.")

            sku = normalize_sku(sku_raw)
            producto = productos_by_sku.get(sku)
            if not producto:
                raise BusinessRuleError(f"El producto con SKU '{sku_raw}' no existe en la empresa activa.")

            precio = _to_decimal(row.get("precio"))
            descuento_maximo = _to_decimal(row.get("descuento_maximo"), default=Decimal("0"))
            if precio == Decimal("0"):
                warnings.append(
                    _build_zero_price_warning(
                        line_number=line_number,
                        sku=sku,
                        producto_nombre=producto.nombre,
                    )
                )

            item_existente = items_existentes.get(producto.id)
            if item_existente is None:
                item_existente = _get_existing_item(empresa=empresa, lista=lista, producto=producto)
                if item_existente is not None:
                    items_existentes[producto.id] = item_existente
            payload = {
                "lista": lista,
                "producto": producto,
                "precio": precio,
                "descuento_maximo": descuento_maximo,
            }

            if item_existente:
                if dry_run:
                    _validar_item_preview(
                        empresa=empresa,
                        lista=lista,
                        producto=producto,
                        precio=precio,
                        descuento_maximo=descuento_maximo,
                    )
                else:
                    ListaPrecioItemService.actualizar_item(
                        item_id=item_existente.id,
                        empresa=empresa,
                        usuario=user,
                        data=payload,
                    )
                updated += 1
            else:
                if dry_run:
                    _validar_item_preview(
                        empresa=empresa,
                        lista=lista,
                        producto=producto,
                        precio=precio,
                        descuento_maximo=descuento_maximo,
                    )
                else:
                    try:
                        item = ListaPrecioItemService.crear_item(
                            empresa=empresa,
                            usuario=user,
                            data=payload,
                        )
                        items_existentes[producto.id] = item
                        created += 1
                    except ConflictError:
                        # Si otro flujo ya creo el item o el lookup previo no lo detecto,
                        # degradamos a actualizacion para mantener la importacion idempotente.
                        item_existente = _get_existing_item(empresa=empresa, lista=lista, producto=producto)
                        if item_existente is None:
                            raise
                        ListaPrecioItemService.actualizar_item(
                            item_id=item_existente.id,
                            empresa=empresa,
                            usuario=user,
                            data=payload,
                        )
                        items_existentes[producto.id] = item_existente
                        updated += 1
                if dry_run:
                    created += 1
        except Exception as exc:  # pragma: no cover - resiliencia por fila
            errors.append(
                {
                    "line": line_number,
                    "sku": row.get("sku") or "",
                    "detail": format_bulk_import_row_error(exc),
                }
            )

    result = {
        "lista_id": str(lista.id),
        "lista_nombre": lista.nombre,
        **build_bulk_import_result(
            created=created,
            updated=updated,
            errors=errors,
            warnings=warnings,
            total_rows=len(rows),
            dry_run=dry_run,
        ),
    }
    if dry_run:
        return result

    _registrar_resumen_importacion(
        empresa=empresa,
        user=user,
        lista=lista,
        payload={
            "lista_id": str(lista.id),
            "lista_nombre": lista.nombre,
            "created": created,
            "updated": updated,
            "errors": len(errors),
            "warnings": len(warnings),
            "total_rows": len(rows),
            "successful_rows": created + updated,
        },
    )
    return result


def build_lista_precio_bulk_template(*, user, empresa, lista_id):
    """Construye la plantilla XLSX oficial para carga masiva de items de una lista de precio."""
    empresa = _resolve_import_empresa(user, empresa)
    _ensure_admin_user(user, empresa)
    lista = _get_lista_activa(lista_id=lista_id, empresa=empresa)

    headers = ["sku", "precio", "descuento_maximo"]
    sample = ["SKU-DEMO-001", "44990", "5"]
    instructions = [
        f"MODULO PRODUCTOS: use esta plantilla solo para la lista '{lista.nombre}'.",
        "Columnas obligatorias: sku, precio.",
        "sku debe existir previamente en el catalogo de productos de la empresa activa.",
        "descuento_maximo es opcional y debe estar entre 0 y 100.",
        "Si el SKU ya existe en la lista, su precio se actualizara.",
        "Si el SKU no existe en la lista, se agregara como nuevo item comercial.",
        "No incluya nombre de lista ni cliente; la importacion siempre aplica sobre la lista seleccionada.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="ListaPrecioItems",
        template_title=f"Plantilla de importacion - Lista de precio {lista.nombre}",
    )
