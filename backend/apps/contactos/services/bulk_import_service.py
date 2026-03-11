from decimal import Decimal, InvalidOperation

from apps.contactos.models import Cliente, Contacto, Proveedor
from apps.contactos.models.contacto import TipoContacto
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.core.roles import RolUsuario
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.xlsx_template import build_xlsx_template
from apps.core.validators import formatear_rut


def _to_bool(raw_value, *, default=True):
    value = str(raw_value or "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "t", "si", "s", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise BusinessRuleError("Valor booleano invalido.")


def _to_int(raw_value, *, default=0):
    value = str(raw_value or "").strip()
    if not value:
        return default
    try:
        return int(float(value.replace(",", ".")))
    except ValueError as exc:
        raise BusinessRuleError("Valor entero invalido.") from exc


def _to_decimal(raw_value, *, default=Decimal("0")):
    value = str(raw_value or "").strip()
    if not value:
        return default

    normalized = value.replace(" ", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise BusinessRuleError("Valor numerico invalido.") from exc


def _normalize_text(value):
    return str(value or "").strip()


def _normalize_rut(value):
    raw = _normalize_text(value)
    if not raw:
        return ""
    return formatear_rut(raw)


def _normalize_tipo_contacto(raw_value):
    value = _normalize_text(raw_value).upper()
    if not value:
        return TipoContacto.EMPRESA

    empresa_aliases = {
        "EMPRESA", "E", "JURIDICA", "JURIDICO", "COMPANIA", "COMPANIA", "COMPANY", "PYME",
    }
    persona_aliases = {
        "PERSONA", "P", "NATURAL", "INDIVIDUAL",
    }

    if value in empresa_aliases:
        return TipoContacto.EMPRESA
    if value in persona_aliases:
        return TipoContacto.PERSONA

    # Compatibility: some users upload product templates with PRODUCTO/SERVICIO.
    if value in {"PRODUCTO", "SERVICIO"}:
        return TipoContacto.EMPRESA

    raise BusinessRuleError(
        "Tipo invalido. Use EMPRESA o PERSONA.",
    )


def _ensure_admin_user(user, empresa):
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


def _find_or_create_contacto(row, *, empresa, user):
    rut = _normalize_rut(row.get("rut"))
    nombre = _normalize_text(row.get("nombre"))
    if not nombre:
        raise BusinessRuleError("El nombre es obligatorio.")

    email = _normalize_text(row.get("email"))
    tipo = _normalize_tipo_contacto(row.get("tipo"))

    contacto = None
    if rut:
        contacto = Contacto.all_objects.filter(empresa=empresa, rut=rut).first()

    if not contacto and nombre and email:
        contacto = Contacto.all_objects.filter(
            empresa=empresa,
            nombre__iexact=nombre,
            email__iexact=email,
        ).first()

    contacto_fields = {
        "empresa": empresa,
        "creado_por": user,
        "nombre": nombre,
        "razon_social": _normalize_text(row.get("razon_social")) or None,
        "rut": rut or None,
        "tipo": tipo,
        "email": email or None,
        "telefono": _normalize_text(row.get("telefono")) or None,
        "celular": _normalize_text(row.get("celular")) or None,
        "notas": _normalize_text(row.get("notas")) or None,
        "activo": _to_bool(row.get("activo"), default=True),
    }

    created = False
    updated = False
    if contacto:
        for key, value in contacto_fields.items():
            if key in {"empresa", "creado_por"}:
                continue
            if value is not None and _normalize_text(value) != "":
                setattr(contacto, key, value)
        contacto.save()
        updated = True
    else:
        contacto = Contacto(**contacto_fields)
        contacto.save()
        created = True

    return contacto, created, updated


def import_clientes(*, uploaded_file, user, empresa):
    _ensure_admin_user(user, empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["nombre"],
    )

    created = 0
    updated = 0
    errors = []

    for line_number, row in rows:
        try:
            contacto, _created_contacto, _updated_contacto = _find_or_create_contacto(row, empresa=empresa, user=user)

            cliente = Cliente.all_objects.filter(empresa=empresa, contacto=contacto).first()
            cliente_fields = {
                "empresa": empresa,
                "creado_por": user,
                "contacto": contacto,
                "limite_credito": _to_decimal(row.get("limite_credito"), default=Decimal("0")),
                "dias_credito": _to_int(row.get("dias_credito"), default=0),
                "categoria_cliente": _normalize_text(row.get("categoria_cliente")) or None,
                "segmento": _normalize_text(row.get("segmento")) or None,
            }

            if cliente:
                for key, value in cliente_fields.items():
                    if key in {"empresa", "creado_por", "contacto"}:
                        continue
                    setattr(cliente, key, value)
                cliente.save()
                updated += 1
            else:
                Cliente(**cliente_fields).save()
                created += 1
        except Exception as exc:  # pragma: no cover - defensive guard for row-level resilience
            errors.append(
                {
                    "line": line_number,
                    "nombre": row.get("nombre") or "",
                    "detail": str(exc),
                }
            )

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_rows": len(rows),
        "successful_rows": created + updated,
    }


def import_proveedores(*, uploaded_file, user, empresa):
    _ensure_admin_user(user, empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["nombre"],
    )

    created = 0
    updated = 0
    errors = []

    for line_number, row in rows:
        try:
            contacto, _created_contacto, _updated_contacto = _find_or_create_contacto(row, empresa=empresa, user=user)

            proveedor = Proveedor.all_objects.filter(empresa=empresa, contacto=contacto).first()
            proveedor_fields = {
                "empresa": empresa,
                "creado_por": user,
                "contacto": contacto,
                "giro": _normalize_text(row.get("giro")) or None,
                "vendedor_contacto": _normalize_text(row.get("vendedor_contacto")) or None,
                "dias_credito": _to_int(row.get("dias_credito"), default=0),
            }

            if proveedor:
                for key, value in proveedor_fields.items():
                    if key in {"empresa", "creado_por", "contacto"}:
                        continue
                    setattr(proveedor, key, value)
                proveedor.save()
                updated += 1
            else:
                Proveedor(**proveedor_fields).save()
                created += 1
        except Exception as exc:  # pragma: no cover - defensive guard for row-level resilience
            errors.append(
                {
                    "line": line_number,
                    "nombre": row.get("nombre") or "",
                    "detail": str(exc),
                }
            )

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "total_rows": len(rows),
        "successful_rows": created + updated,
    }


def build_clientes_bulk_template(*, user, empresa):
    _ensure_admin_user(user, empresa)

    headers = [
        "nombre",
        "rut",
        "email",
        "tipo",
        "razon_social",
        "telefono",
        "celular",
        "notas",
        "activo",
        "limite_credito",
        "dias_credito",
        "categoria_cliente",
        "segmento",
    ]

    sample = [
        "Ferreteria Central SpA",
        "12345678-5",
        "compras@ferrecentral.cl",
        "EMPRESA",
        "Ferreteria Central SpA",
        "22223333",
        "99998888",
        "Cliente preferente",
        "true",
        "500000",
        "30",
        "ORO",
        "RETAIL",
    ]

    instructions = [
        "MODULO CLIENTES: use esta plantilla solo para clientes.",
        "Columnas obligatorias: nombre.",
        "tipo permitido: EMPRESA o PERSONA.",
        "NO usar PRODUCTO/SERVICIO en esta plantilla.",
        "activo: true/false.",
        "Si rut existe en la empresa, se actualiza ese contacto.",
        "Si no hay rut, se intenta match por nombre + email.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="Clientes",
    )


def build_proveedores_bulk_template(*, user, empresa):
    _ensure_admin_user(user, empresa)

    headers = [
        "nombre",
        "rut",
        "email",
        "tipo",
        "razon_social",
        "telefono",
        "celular",
        "notas",
        "activo",
        "giro",
        "vendedor_contacto",
        "dias_credito",
    ]

    sample = [
        "Aceros del Sur Ltda",
        "22333444-6",
        "ventas@acerosdelsur.cl",
        "EMPRESA",
        "Aceros del Sur Ltda",
        "22334455",
        "98887766",
        "Despacha en 48 horas",
        "true",
        "Metalurgica",
        "Maria Lopez",
        "15",
    ]

    instructions = [
        "MODULO PROVEEDORES: use esta plantilla solo para proveedores.",
        "Columnas obligatorias: nombre.",
        "tipo permitido: EMPRESA o PERSONA.",
        "NO usar PRODUCTO/SERVICIO en esta plantilla.",
        "activo: true/false.",
        "Si rut existe en la empresa, se actualiza ese contacto.",
        "Si no hay rut, se intenta match por nombre + email.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="Proveedores",
    )
