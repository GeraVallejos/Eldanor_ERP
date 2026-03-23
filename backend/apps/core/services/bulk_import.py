from collections.abc import Mapping, Sequence
from contextlib import contextmanager, nullcontext

from django.db import transaction


@contextmanager
def bulk_import_execution_context(*, dry_run=False):
    """Ejecuta una importacion en transaccion reversible cuando se solicita previsualizacion."""
    with (transaction.atomic() if dry_run else nullcontext()):
        yield
        if dry_run:
            transaction.set_rollback(True)


def build_bulk_import_result(*, created, updated, errors, total_rows, warnings=None, dry_run=False):
    """Construye el contrato API estandar para respuestas de carga masiva."""
    normalized_warnings = list(warnings or [])
    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "warnings": normalized_warnings,
        "total_rows": total_rows,
        "successful_rows": created + updated,
        "dry_run": dry_run,
    }


def flatten_bulk_import_error_detail(detail):
    """Convierte estructuras de error complejas en un mensaje corto y legible."""
    if isinstance(detail, Mapping):
        messages = []
        for field, value in detail.items():
            nested = flatten_bulk_import_error_detail(value)
            if not nested:
                continue
            if field in {"__all__", "non_field_errors"}:
                messages.append(nested)
            else:
                messages.append(f"{field}: {nested}")
        return "; ".join(messages)

    if isinstance(detail, Sequence) and not isinstance(detail, (str, bytes, bytearray)):
        messages = [flatten_bulk_import_error_detail(item) for item in detail]
        return "; ".join(message for message in messages if message)

    if detail is None:
        return ""

    return str(detail)


def format_bulk_import_row_error(exc):
    """Normaliza errores por fila para evitar mensajes tecnicos crudos en la UI."""
    if getattr(exc, "message_dict", None):
        return flatten_bulk_import_error_detail(exc.message_dict)
    if getattr(exc, "messages", None):
        return flatten_bulk_import_error_detail(exc.messages)

    detail = getattr(exc, "detail", None)
    if detail is not None:
        normalized = flatten_bulk_import_error_detail(detail)
        if normalized:
            return normalized

    return flatten_bulk_import_error_detail(str(exc))
