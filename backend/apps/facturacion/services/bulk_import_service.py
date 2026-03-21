from django.utils.dateparse import parse_date

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.core.roles import RolUsuario
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.domain_event_service import DomainEventService
from apps.core.services.outbox_service import OutboxService
from apps.core.services.xlsx_template import build_xlsx_template
from apps.facturacion.models import RangoFolioTributario, TipoDocumentoTributario


def _normalize_text(value):
    return str(value or "").strip()


def _to_optional_date(raw_value, *, field_name):
    value = _normalize_text(raw_value)
    if not value:
        return None
    parsed = parse_date(value)
    if not parsed:
        raise BusinessRuleError(f"El campo {field_name} debe usar formato YYYY-MM-DD.")
    return parsed


def _to_optional_int(raw_value, *, field_name):
    value = _normalize_text(raw_value)
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise BusinessRuleError(f"El campo {field_name} debe ser entero.") from exc


def _to_bool(raw_value, *, default=True):
    value = _normalize_text(raw_value).lower()
    if not value:
        return default
    if value in {"1", "true", "t", "si", "s", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise BusinessRuleError("Valor booleano invalido.")


def _ensure_admin_user(user, empresa):
    """Restringe configuracion tributaria masiva a administracion."""
    if getattr(user, "is_superuser", False):
        return

    if not empresa:
        raise AuthorizationError(
            "No hay empresa activa para esta operacion.",
            error_code="BULK_IMPORT_NO_EMPRESA",
        )

    rol = user.get_rol_en_empresa(empresa)
    if rol not in {RolUsuario.OWNER, RolUsuario.ADMIN}:
        raise AuthorizationError(
            "Solo administracion puede ejecutar carga masiva tributaria.",
            error_code="BULK_IMPORT_ADMIN_ONLY",
        )


def _normalize_tipo_documento(value):
    normalized = _normalize_text(value).upper()
    mapping = {
        "FACTURA_VENTA": TipoDocumentoTributario.FACTURA_VENTA,
        "FACTURA": TipoDocumentoTributario.FACTURA_VENTA,
        "GUIA_DESPACHO": TipoDocumentoTributario.GUIA_DESPACHO,
        "GUIA": TipoDocumentoTributario.GUIA_DESPACHO,
        "NOTA_CREDITO_VENTA": TipoDocumentoTributario.NOTA_CREDITO_VENTA,
        "NOTA_CREDITO": TipoDocumentoTributario.NOTA_CREDITO_VENTA,
    }
    if normalized not in mapping:
        raise BusinessRuleError("Tipo_documento invalido para folios tributarios.")
    return mapping[normalized]


def _registrar_resumen_importacion(*, empresa, user, payload):
    """Registra auditoria y eventos para la importacion tributaria."""
    DomainEventService.record_event(
        empresa=empresa,
        aggregate_type="RangoFolioTributarioBulkImport",
        aggregate_id=empresa.id,
        event_type="tributario.rangos_folios.bulk_import.finalizado",
        payload=payload,
        meta={"source": "tributario_bulk_import_service"},
        idempotency_key=f"tributario-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
        usuario=user,
    )
    OutboxService.enqueue(
        empresa=empresa,
        topic="sii.folios.bulk_import",
        event_name="rangos_folios.bulk_import.finalizado",
        payload=payload,
        usuario=user,
        dedup_key=f"tributario-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )
    AuditoriaService.registrar_evento(
        empresa=empresa,
        usuario=user,
        module_code="FACTURACION",
        action_code="EDITAR",
        event_type="TRIBUTARIO_BULK_IMPORT",
        entity_type="RANGO_FOLIO_TRIBUTARIO",
        summary="Carga masiva de rangos tributarios ejecutada.",
        severity=AuditSeverity.INFO,
        changes={
            "registros_creados": [0, int(payload["created"])],
            "registros_actualizados": [0, int(payload["updated"])],
            "filas_con_error": [0, int(payload["errors"])],
        },
        payload=payload,
        source="tributario_bulk_import_service",
        idempotency_key=f"audit:tributario-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )


def import_rangos_folios_tributarios(*, uploaded_file, user, empresa):
    """Importa rangos CAF por tipo de documento para la empresa activa."""
    _ensure_admin_user(user, empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["tipo_documento", "caf_nombre", "folio_desde", "folio_hasta"],
    )

    created = 0
    updated = 0
    errors = []

    for line_number, row in rows:
        try:
            tipo_documento = _normalize_tipo_documento(row.get("tipo_documento"))
            caf_nombre = _normalize_text(row.get("caf_nombre"))
            if not caf_nombre:
                raise BusinessRuleError("caf_nombre es obligatorio.")

            folio_desde = _to_optional_int(row.get("folio_desde"), field_name="folio_desde")
            folio_hasta = _to_optional_int(row.get("folio_hasta"), field_name="folio_hasta")
            if folio_desde is None or folio_hasta is None:
                raise BusinessRuleError("Debe informar folio_desde y folio_hasta.")

            existing = RangoFolioTributario.all_objects.filter(
                empresa=empresa,
                tipo_documento=tipo_documento,
                folio_desde=folio_desde,
                folio_hasta=folio_hasta,
            ).first()

            payload = {
                "empresa": empresa,
                "creado_por": user,
                "tipo_documento": tipo_documento,
                "caf_nombre": caf_nombre,
                "folio_desde": folio_desde,
                "folio_hasta": folio_hasta,
                "folio_actual": _to_optional_int(row.get("folio_actual"), field_name="folio_actual"),
                "fecha_autorizacion": _to_optional_date(row.get("fecha_autorizacion"), field_name="fecha_autorizacion"),
                "fecha_vencimiento": _to_optional_date(row.get("fecha_vencimiento"), field_name="fecha_vencimiento"),
                "activo": _to_bool(row.get("activo"), default=True),
            }

            if existing:
                for key, value in payload.items():
                    if key in {"empresa", "creado_por"}:
                        continue
                    setattr(existing, key, value)
                existing.save()
                updated += 1
            else:
                RangoFolioTributario.all_objects.create(**payload)
                created += 1
        except Exception as exc:  # pragma: no cover
            errors.append(
                {
                    "line": line_number,
                    "tipo_documento": row.get("tipo_documento") or "",
                    "detail": str(exc),
                }
            )

    result = {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_rows": len(rows),
        "successful_rows": created + updated,
    }
    _registrar_resumen_importacion(
        empresa=empresa,
        user=user,
        payload={
            "created": created,
            "updated": updated,
            "errors": len(errors),
            "total_rows": len(rows),
            "successful_rows": created + updated,
        },
    )
    return result


def build_rangos_folios_template(*, user, empresa):
    """Construye la plantilla XLSX oficial para rangos de folios tributarios."""
    _ensure_admin_user(user, empresa)

    headers = [
        "tipo_documento",
        "caf_nombre",
        "folio_desde",
        "folio_hasta",
        "folio_actual",
        "fecha_autorizacion",
        "fecha_vencimiento",
        "activo",
    ]

    sample = [
        "FACTURA_VENTA",
        "CAF FACTURAS 2026",
        "100",
        "500",
        "120",
        "2026-01-01",
        "2026-12-31",
        "true",
    ]

    instructions = [
        "SII / DTE: use esta plantilla para cargar o actualizar rangos CAF.",
        "Columnas obligatorias: tipo_documento, caf_nombre, folio_desde, folio_hasta.",
        "tipo_documento permitido: FACTURA_VENTA, GUIA_DESPACHO, NOTA_CREDITO_VENTA.",
        "Si un rango ya existe con mismo tipo_documento, folio_desde y folio_hasta, se actualiza.",
        "folio_actual es opcional; si queda vacio, el sistema reserva desde folio_desde.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="RangosFolios",
    )

