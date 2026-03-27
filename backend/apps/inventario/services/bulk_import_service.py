from decimal import Decimal, InvalidOperation

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import AppError, BusinessRuleError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import (
    DomainEventService,
    OutboxService,
    build_bulk_import_result,
    bulk_import_execution_context,
    format_bulk_import_row_error,
)
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.xlsx_template import build_xlsx_template
from apps.inventario.services.documento_inventario_service import DocumentoInventarioService
from apps.inventario.models import Bodega
from apps.productos.models import Producto


AJUSTE_BULK_HEADERS = [
    "motivo",
    "referencia_operativa",
    "observaciones",
    "producto_sku",
    "bodega",
    "stock_objetivo",
]

TRASLADO_BULK_HEADERS = [
    "motivo",
    "referencia_operativa",
    "observaciones",
    "bodega_origen",
    "bodega_destino",
    "producto_sku",
    "cantidad",
]


def _normalize_text(value, *, uppercase=False):
    """Normaliza texto libre para comparaciones y payloads de importacion."""
    normalized = str(value or "").strip()
    if uppercase:
        return normalized.upper()
    return normalized


def _to_decimal(raw_value, *, field_name):
    """Convierte una celda numerica a decimal compatible con validaciones del dominio."""
    value = _normalize_text(raw_value)
    if not value:
        raise BusinessRuleError(f"Debe informar {field_name}.")
    normalized = value.replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BusinessRuleError(f"{field_name} invalido.") from exc


def _build_reference(motivo, referencia_operativa, observaciones):
    """Compone una referencia documental legible a partir de columnas del archivo."""
    return " | ".join(
        part
        for part in [motivo, referencia_operativa, observaciones]
        if _normalize_text(part)
    )


def _resolve_producto(*, empresa, sku):
    """Resuelve un producto manejado en inventario a partir de su SKU."""
    normalized_sku = _normalize_text(sku, uppercase=True)
    if not normalized_sku:
        raise BusinessRuleError("Debe informar producto_sku.")

    producto = (
        Producto.all_objects
        .filter(empresa=empresa, sku=normalized_sku, maneja_inventario=True)
        .only("id", "nombre", "sku")
        .first()
    )
    if not producto:
        raise BusinessRuleError(f"No se encontro un producto con SKU {normalized_sku}.")
    return producto


def _resolve_bodega(*, empresa, nombre, allow_blank=False, field_name="bodega"):
    """Resuelve una bodega por nombre normalizado dentro del tenant activo."""
    normalized_name = _normalize_text(nombre, uppercase=True)
    if not normalized_name:
        if allow_blank:
            return None
        raise BusinessRuleError(f"Debe informar {field_name}.")

    bodega = (
        Bodega.all_objects
        .filter(empresa=empresa, nombre=normalized_name)
        .only("id", "nombre")
        .first()
    )
    if not bodega:
        raise BusinessRuleError(f"No se encontro una bodega con nombre {normalized_name}.")
    return bodega


def _ensure_consistent_context(*, current_context, next_context, line_number, errors, extra_reference=None):
    """Valida que el archivo represente un solo documento coherente y auditable."""
    if current_context is None:
        return next_context

    for field, current_value in current_context.items():
        next_value = next_context.get(field)
        if current_value != next_value:
            errors.append(
                {
                    "line": line_number,
                    "detail": f"La columna {field} debe ser consistente en todo el archivo para generar un solo documento.",
                    "referencia": extra_reference or "",
                }
            )
            return None
    return current_context


def _record_bulk_import_side_effects(*, empresa, user, document_type, summary, payload):
    """Registra auditoria y eventos de integracion para la carga masiva de inventario."""
    event_name = f"inventario.{document_type}.bulk_import"
    DomainEventService.record_event(
        empresa=empresa,
        aggregate_type="InventarioBulkImport",
        aggregate_id=empresa.id,
        event_type=event_name,
        payload=payload,
        meta={"source": "inventario.bulk_import_service"},
        idempotency_key=f"{event_name}:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
        usuario=user,
    )
    OutboxService.enqueue(
        empresa=empresa,
        topic="inventario.bulk_import",
        event_name=event_name,
        payload=payload,
        usuario=user,
        dedup_key=f"{event_name}:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )
    AuditoriaService.registrar_evento(
        empresa=empresa,
        usuario=user,
        module_code=Modulos.INVENTARIO,
        action_code=Acciones.EDITAR,
        event_type="INVENTARIO_BULK_IMPORT",
        entity_type=document_type.upper(),
        summary=summary,
        severity=AuditSeverity.INFO,
        changes={
            "filas_totales": [0, int(payload["total_rows"])],
            "filas_exitosas": [0, int(payload["successful_rows"])],
            "filas_con_error": [0, int(payload["errors"])],
        },
        payload=payload,
        source="inventario.bulk_import_service",
        idempotency_key=f"audit:{event_name}:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )


def import_ajustes_masivos_desde_archivo(*, uploaded_file, user, empresa, dry_run=False):
    """Importa un archivo CSV/XLSX de ajustes masivos y genera un borrador validado."""
    rows = parse_csv_upload(uploaded_file, required_headers=["motivo", "producto_sku", "stock_objetivo"])

    errors = []
    items = []
    documento = None
    context = None
    seen_keys = set()

    with bulk_import_execution_context(dry_run=dry_run):
        for line_number, row in rows:
            try:
                producto = _resolve_producto(empresa=empresa, sku=row.get("producto_sku"))
                bodega = _resolve_bodega(
                    empresa=empresa,
                    nombre=row.get("bodega"),
                    allow_blank=True,
                )
                stock_objetivo = _to_decimal(row.get("stock_objetivo"), field_name="stock_objetivo")
                if stock_objetivo < 0:
                    raise BusinessRuleError("stock_objetivo no puede ser negativo.")

                line_context = {
                    "motivo": _normalize_text(row.get("motivo"), uppercase=True),
                    "referencia_operativa": _normalize_text(row.get("referencia_operativa"), uppercase=True),
                    "observaciones": _normalize_text(row.get("observaciones"), uppercase=True),
                }
                if not line_context["motivo"]:
                    raise BusinessRuleError("Debe informar motivo.")

                extra_reference = producto.sku
                next_context = _ensure_consistent_context(
                    current_context=context,
                    next_context=line_context,
                    line_number=line_number,
                    errors=errors,
                    extra_reference=extra_reference,
                )
                if next_context is None:
                    continue
                context = next_context

                dedup_key = (str(producto.id), str(bodega.id) if bodega else "")
                if dedup_key in seen_keys:
                    raise BusinessRuleError("La combinacion producto_sku y bodega no puede repetirse en el archivo.")
                seen_keys.add(dedup_key)

                items.append(
                    {
                        "producto_id": producto.id,
                        "bodega_id": bodega.id if bodega else None,
                        "stock_objetivo": stock_objetivo,
                    }
                )
            except AppError as exc:
                errors.append(
                    {
                        "line": line_number,
                        "detail": format_bulk_import_row_error(exc),
                        "sku": _normalize_text(row.get("producto_sku"), uppercase=True),
                        "referencia": _normalize_text(row.get("bodega"), uppercase=True),
                    }
                )

        result = build_bulk_import_result(
            created=len(items),
            updated=0,
            errors=errors,
            warnings=[],
            total_rows=len(rows),
            dry_run=dry_run,
        )

        if items and context:
            documento = DocumentoInventarioService.guardar_borrador_ajuste_masivo(
                empresa=empresa,
                usuario=user,
                referencia=_build_reference(
                    context["motivo"],
                    context["referencia_operativa"],
                    context["observaciones"],
                ),
                motivo=context["motivo"],
                observaciones=context["observaciones"],
                items=items,
            )

        if dry_run:
            return result, None

    if documento:
        payload = {
            "documento_id": str(documento.id),
            "numero": documento.numero,
            "estado": documento.estado,
            "created": result["created"],
            "updated": result["updated"],
            "errors": len(result["errors"]),
            "total_rows": result["total_rows"],
            "successful_rows": result["successful_rows"],
        }
        _record_bulk_import_side_effects(
            empresa=empresa,
            user=user,
            document_type="ajustes_masivos",
            summary="Carga masiva de ajustes de inventario ejecutada.",
            payload=payload,
        )

    return result, documento


def import_traslados_masivos_desde_archivo(*, uploaded_file, user, empresa, dry_run=False):
    """Importa un archivo CSV/XLSX de traslados masivos y genera un borrador validado."""
    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["motivo", "bodega_origen", "bodega_destino", "producto_sku", "cantidad"],
    )

    errors = []
    items = []
    documento = None
    context = None
    seen_keys = set()

    with bulk_import_execution_context(dry_run=dry_run):
        for line_number, row in rows:
            try:
                producto = _resolve_producto(empresa=empresa, sku=row.get("producto_sku"))
                bodega_origen = _resolve_bodega(
                    empresa=empresa,
                    nombre=row.get("bodega_origen"),
                    field_name="bodega_origen",
                )
                bodega_destino = _resolve_bodega(
                    empresa=empresa,
                    nombre=row.get("bodega_destino"),
                    field_name="bodega_destino",
                )
                if str(bodega_origen.id) == str(bodega_destino.id):
                    raise BusinessRuleError("La bodega destino debe ser distinta a la bodega origen.")

                cantidad = _to_decimal(row.get("cantidad"), field_name="cantidad")
                if cantidad <= 0:
                    raise BusinessRuleError("cantidad debe ser mayor a cero.")

                line_context = {
                    "motivo": _normalize_text(row.get("motivo"), uppercase=True),
                    "referencia_operativa": _normalize_text(row.get("referencia_operativa"), uppercase=True),
                    "observaciones": _normalize_text(row.get("observaciones"), uppercase=True),
                    "bodega_origen_id": str(bodega_origen.id),
                    "bodega_destino_id": str(bodega_destino.id),
                }
                if not line_context["motivo"]:
                    raise BusinessRuleError("Debe informar motivo.")

                next_context = _ensure_consistent_context(
                    current_context=context,
                    next_context=line_context,
                    line_number=line_number,
                    errors=errors,
                    extra_reference=producto.sku,
                )
                if next_context is None:
                    continue
                context = next_context

                dedup_key = str(producto.id)
                if dedup_key in seen_keys:
                    raise BusinessRuleError("producto_sku no puede repetirse en el archivo de traslado.")
                seen_keys.add(dedup_key)

                items.append(
                    {
                        "producto_id": producto.id,
                        "cantidad": cantidad,
                    }
                )
            except AppError as exc:
                errors.append(
                    {
                        "line": line_number,
                        "detail": format_bulk_import_row_error(exc),
                        "sku": _normalize_text(row.get("producto_sku"), uppercase=True),
                        "referencia": f"{_normalize_text(row.get('bodega_origen'), uppercase=True)}->{_normalize_text(row.get('bodega_destino'), uppercase=True)}",
                    }
                )

        result = build_bulk_import_result(
            created=len(items),
            updated=0,
            errors=errors,
            warnings=[],
            total_rows=len(rows),
            dry_run=dry_run,
        )

        if items and context:
            documento = DocumentoInventarioService.guardar_borrador_traslado_masivo(
                empresa=empresa,
                usuario=user,
                referencia=_build_reference(
                    context["motivo"],
                    context["referencia_operativa"],
                    context["observaciones"],
                ),
                motivo=context["motivo"],
                observaciones=context["observaciones"],
                bodega_origen_id=context["bodega_origen_id"],
                bodega_destino_id=context["bodega_destino_id"],
                items=items,
            )

        if dry_run:
            return result, None

    if documento:
        payload = {
            "documento_id": str(documento.id),
            "numero": documento.numero,
            "estado": documento.estado,
            "created": result["created"],
            "updated": result["updated"],
            "errors": len(result["errors"]),
            "total_rows": result["total_rows"],
            "successful_rows": result["successful_rows"],
        }
        _record_bulk_import_side_effects(
            empresa=empresa,
            user=user,
            document_type="traslados_masivos",
            summary="Carga masiva de traslados de inventario ejecutada.",
            payload=payload,
        )

    return result, documento


def build_ajustes_masivos_bulk_template(*, user, empresa):
    """Construye la plantilla XLSX recomendada para importar ajustes masivos."""
    if not user or not empresa:
        raise BusinessRuleError("Contexto invalido para construir la plantilla.")
    return build_xlsx_template(
        headers=AJUSTE_BULK_HEADERS,
        sample_row=[
            "CONTEO CICLICO",
            "PASILLO NORTE",
            "REVISION SEMANAL",
            "SKU-001",
            "CASA MATRIZ",
            "15",
        ],
        instructions=[
            "Cada archivo genera un solo documento borrador de ajuste masivo.",
            "MOTIVO, REFERENCIA_OPERATIVA y OBSERVACIONES deben ser consistentes en todas las filas.",
            "BODEGA es opcional; si queda vacia, el ajuste se registra sin bodega explicita.",
            "PRODUCTO_SKU debe existir y STOCK_OBJETIVO no puede ser negativo.",
        ],
        sheet_name="AjustesMasivos",
        template_title="Plantilla de importacion - Ajustes masivos de inventario",
    )


def build_traslados_masivos_bulk_template(*, user, empresa):
    """Construye la plantilla XLSX recomendada para importar traslados masivos."""
    if not user or not empresa:
        raise BusinessRuleError("Contexto invalido para construir la plantilla.")
    return build_xlsx_template(
        headers=TRASLADO_BULK_HEADERS,
        sample_row=[
            "CAMBIO DE LAYOUT",
            "REUBICACION DE PASILLO",
            "REPOSICION DE EXHIBICION",
            "CASA MATRIZ",
            "SALA DE VENTAS",
            "SKU-001",
            "4",
        ],
        instructions=[
            "Cada archivo genera un solo documento borrador de traslado masivo.",
            "MOTIVO, REFERENCIA_OPERATIVA, OBSERVACIONES, BODEGA_ORIGEN y BODEGA_DESTINO deben ser consistentes en todas las filas.",
            "BODEGA_DESTINO debe ser distinta de BODEGA_ORIGEN.",
            "PRODUCTO_SKU debe existir y CANTIDAD debe ser mayor a cero.",
        ],
        sheet_name="TrasladosMasivos",
        template_title="Plantilla de importacion - Traslados masivos de inventario",
    )
