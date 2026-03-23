from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_date

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.core.roles import RolUsuario
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.domain_event_service import DomainEventService
from apps.core.services.outbox_service import OutboxService
from apps.core.services.bulk_import import (
    build_bulk_import_result,
    bulk_import_execution_context,
    format_bulk_import_row_error,
)
from apps.core.services.xlsx_template import build_xlsx_template
from apps.tesoreria.models import CuentaBancariaEmpresa, MovimientoBancario, OrigenMovimientoBancario


def _normalize_text(value):
    return str(value or "").strip()


def _to_bool(raw_value, *, default=True):
    value = _normalize_text(raw_value).lower()
    if not value:
        return default
    if value in {"1", "true", "t", "si", "s", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise BusinessRuleError("Valor booleano invalido.")


def _to_decimal(raw_value, *, default=Decimal("0")):
    value = _normalize_text(raw_value)
    if not value:
        return default

    normalized = value.replace(" ", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise BusinessRuleError("Valor numerico invalido.") from exc


def _to_date(raw_value, *, field_name):
    value = _normalize_text(raw_value)
    if not value:
        raise BusinessRuleError(f"El campo {field_name} es obligatorio.")

    parsed = parse_date(value)
    if not parsed:
        raise BusinessRuleError(f"El campo {field_name} debe usar formato YYYY-MM-DD.")
    return parsed


def _ensure_admin_user(user, empresa):
    """Restringe operaciones de backoffice a usuarios administradores u owner."""
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
            "Solo administracion puede ejecutar carga masiva bancaria.",
            error_code="BULK_IMPORT_ADMIN_ONLY",
        )


def _resolve_cuenta_bancaria(*, empresa, row):
    numero_cuenta = _normalize_text(row.get("numero_cuenta"))
    alias = _normalize_text(row.get("alias_cuenta"))

    if numero_cuenta:
        cuenta = CuentaBancariaEmpresa.all_objects.filter(
            empresa=empresa,
            numero_cuenta=numero_cuenta,
        ).first()
        if cuenta:
            return cuenta

    if alias:
        cuentas = list(
            CuentaBancariaEmpresa.all_objects.filter(
                empresa=empresa,
                alias__iexact=alias,
            )[:2]
        )
        if len(cuentas) == 1:
            return cuentas[0]
        if len(cuentas) > 1:
            raise BusinessRuleError(
                "Existe mas de una cuenta bancaria con ese alias. Use numero_cuenta.",
            )

    raise BusinessRuleError(
        "No se pudo resolver la cuenta bancaria. Use numero_cuenta o alias_cuenta existente.",
    )


def _registrar_resumen_importacion(*, empresa, user, payload):
    """Registra auditoria y eventos para la importacion de movimientos bancarios."""
    DomainEventService.record_event(
        empresa=empresa,
        aggregate_type="MovimientoBancarioBulkImport",
        aggregate_id=empresa.id,
        event_type="tesoreria.movimientos_bancarios.bulk_import.finalizado",
        payload=payload,
        meta={"source": "tesoreria_bulk_import_service"},
        idempotency_key=f"tesoreria-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
        usuario=user,
    )
    OutboxService.enqueue(
        empresa=empresa,
        topic="tesoreria.banco.bulk_import",
        event_name="movimientos_bancarios.bulk_import.finalizado",
        payload=payload,
        usuario=user,
        dedup_key=f"tesoreria-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )
    AuditoriaService.registrar_evento(
        empresa=empresa,
        usuario=user,
        module_code="TESORERIA",
        action_code="CONCILIAR",
        event_type="TESORERIA_BULK_IMPORT",
        entity_type="MOVIMIENTO_BANCARIO",
        summary="Carga masiva de movimientos bancarios ejecutada.",
        severity=AuditSeverity.INFO,
        changes={
            "registros_creados": [0, int(payload["created"])],
            "registros_actualizados": [0, int(payload["updated"])],
            "filas_con_error": [0, int(payload["errors"])],
        },
        payload=payload,
        source="tesoreria_bulk_import_service",
        idempotency_key=f"audit:tesoreria-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )


def import_movimientos_bancarios(*, uploaded_file, user, empresa, dry_run=False):
    """Importa movimientos bancarios desde CSV/XLSX sin conciliar automaticamente."""
    _ensure_admin_user(user, empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["fecha", "tipo", "monto"],
    )

    created = 0
    updated = 0
    errors = []

    with bulk_import_execution_context(dry_run=dry_run):
        for line_number, row in rows:
            try:
                cuenta_bancaria = _resolve_cuenta_bancaria(empresa=empresa, row=row)
                fecha = _to_date(row.get("fecha"), field_name="fecha")
                tipo = _normalize_text(row.get("tipo")).upper()
                if tipo not in {"CREDITO", "DEBITO"}:
                    raise BusinessRuleError("Tipo invalido. Use CREDITO o DEBITO.")

                monto = _to_decimal(row.get("monto"))
                if monto <= 0:
                    raise BusinessRuleError("El monto del movimiento debe ser mayor a cero.")

                referencia = _normalize_text(row.get("referencia"))
                descripcion = _normalize_text(row.get("descripcion"))
                activa = _to_bool(row.get("activo"), default=True)

                existing = MovimientoBancario.all_objects.filter(
                    empresa=empresa,
                    cuenta_bancaria=cuenta_bancaria,
                    fecha=fecha,
                    tipo=tipo,
                    monto=monto,
                    referencia=referencia,
                ).first()

                payload = {
                    "empresa": empresa,
                    "creado_por": user,
                    "cuenta_bancaria": cuenta_bancaria,
                    "fecha": fecha,
                    "referencia": referencia,
                    "descripcion": descripcion,
                    "tipo": tipo,
                    "monto": monto,
                    "origen": OrigenMovimientoBancario.IMPORTACION,
                }

                if existing:
                    existing.descripcion = descripcion or existing.descripcion
                    existing.origen = OrigenMovimientoBancario.IMPORTACION
                    if not activa and not existing.conciliado:
                        existing.conciliado = False
                    existing.save(update_fields=["descripcion", "origen", "conciliado", "actualizado_en"])
                    updated += 1
                else:
                    MovimientoBancario.all_objects.create(**payload)
                    created += 1
            except Exception as exc:  # pragma: no cover
                errors.append(
                    {
                        "line": line_number,
                        "referencia": row.get("referencia") or "",
                        "detail": format_bulk_import_row_error(exc),
                    }
                )

        result = build_bulk_import_result(
            created=created,
            updated=updated,
            errors=errors,
            warnings=[],
            total_rows=len(rows),
            dry_run=dry_run,
        )
        if dry_run:
            return result
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


def build_movimientos_bancarios_template(*, user, empresa):
    """Construye la plantilla XLSX oficial para importacion de movimientos bancarios."""
    _ensure_admin_user(user, empresa)

    headers = [
        "numero_cuenta",
        "alias_cuenta",
        "fecha",
        "tipo",
        "monto",
        "referencia",
        "descripcion",
    ]

    sample = [
        "123456789",
        "BANCO PRINCIPAL",
        "2026-03-19",
        "CREDITO",
        "125000",
        "DEP-001",
        "Deposito cliente factura FV-000123",
    ]

    instructions = [
        "TESORERIA BANCARIA: use esta plantilla para cargar cartolas normalizadas.",
        "Columnas obligatorias: fecha, tipo, monto.",
        "Se recomienda informar numero_cuenta. alias_cuenta sirve como respaldo.",
        "tipo permitido: CREDITO o DEBITO.",
        "No se concilia automaticamente al importar.",
        "Si ya existe un movimiento con misma cuenta, fecha, tipo, monto y referencia, se actualiza descripcion.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="MovimientosBancarios",
        template_title="Plantilla de importacion - Movimientos bancarios",
    )
