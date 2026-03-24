from decimal import Decimal, InvalidOperation
import re

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.tesoreria.models import Moneda
from apps.core.roles import RolUsuario
from apps.core.services import (
    DomainEventService,
    OutboxService,
    build_bulk_import_result,
    bulk_import_execution_context,
    format_bulk_import_row_error,
)
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.xlsx_template import build_xlsx_template
from apps.productos.models import Categoria, Impuesto, Producto, TipoProducto, UnidadMedida
from apps.productos.services.catalogo_service import CategoriaService, ImpuestoService
from apps.productos.services.producto_service import ProductoService
from apps.productos.validators import normalize_sku


def _to_bool(raw_value, *, default=True):
    value = str(raw_value or "").strip().lower()
    if not value:
        return default
    if value in {"1", "true", "t", "si", "s", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise BusinessRuleError("Valor booleano invalido.")


def _to_decimal(raw_value, *, default=Decimal("0")):
    value = str(raw_value or "").strip()
    if not value:
        return default

    normalized = value.replace(" ", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise BusinessRuleError("Valor numerico invalido.") from exc


def _normalize_name(value):
    return str(value or "").strip().upper()


def _get_or_create_categoria(*, categoria_name, categorias, empresa, user):
    """Resuelve una categoria existente o la crea con el servicio de catalogo."""
    categoria = categorias.get(categoria_name)
    if categoria:
        return categoria, False

    categoria = Categoria.all_objects.filter(
        empresa=empresa,
        nombre__iexact=categoria_name,
    ).first()
    if categoria:
        categorias[categoria_name] = categoria
        return categoria, False

    categoria = CategoriaService.crear_categoria(
        empresa=empresa,
        usuario=user,
        data={
            "nombre": categoria_name,
            "descripcion": "",
            "activa": True,
        },
    )
    categorias[categoria_name] = categoria
    return categoria, True


def _extract_impuesto_porcentaje(impuesto_name):
    if not impuesto_name:
        return None

    match = re.search(r"(\d+(?:[\.,]\d+)?)", str(impuesto_name))
    if not match:
        return None

    try:
        return Decimal(match.group(1).replace(",", "."))
    except InvalidOperation:
        return None


def _get_or_create_impuesto(*, impuesto_name, impuestos, empresa, user):
    """Resuelve un impuesto existente o lo crea con trazabilidad consistente."""
    impuesto = impuestos.get(impuesto_name)
    if impuesto:
        return impuesto, False

    impuesto = Impuesto.all_objects.filter(
        empresa=empresa,
        nombre__iexact=impuesto_name,
    ).first()
    if impuesto:
        impuestos[impuesto_name] = impuesto
        return impuesto, False

    porcentaje = _extract_impuesto_porcentaje(impuesto_name)
    if porcentaje is not None:
        impuesto_by_pct = Impuesto.all_objects.filter(
            empresa=empresa,
            porcentaje=porcentaje,
        ).first()
        if impuesto_by_pct:
            impuestos[impuesto_name] = impuesto_by_pct
            return impuesto_by_pct, False
    else:
        porcentaje = Decimal("19")

    impuesto = ImpuestoService.crear_impuesto(
        empresa=empresa,
        usuario=user,
        data={
            "nombre": impuesto_name,
            "porcentaje": porcentaje,
            "activo": True,
        },
    )

    impuestos[impuesto_name] = impuesto
    return impuesto, True


def _resolve_moneda(*, raw_value, monedas, empresa):
    value = _normalize_name(raw_value)
    if not value:
        return None

    moneda = monedas.get(value)
    if moneda:
        return moneda

    moneda = Moneda.all_objects.filter(empresa=empresa, codigo__iexact=value).first()
    if moneda:
        monedas[value] = moneda
        return moneda

    moneda = Moneda.all_objects.filter(empresa=empresa, nombre__iexact=value).first()
    if moneda:
        monedas[value] = moneda
        return moneda

    raise BusinessRuleError(f"La moneda '{raw_value}' no existe para la empresa activa.")


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


def _resolve_import_empresa(user, empresa):
    if empresa:
        return empresa

    user_empresa = getattr(user, "empresa_activa", None)
    if user_empresa:
        return user_empresa

    if hasattr(user, "empresas_rel"):
        relacion = (
            user.empresas_rel.filter(activo=True)
            .select_related("empresa")
            .first()
        )
        if relacion:
            return relacion.empresa

    raise BusinessRuleError(
        "No hay empresa activa para ejecutar la carga masiva.",
        error_code="BULK_IMPORT_NO_EMPRESA",
    )


def _append_warning(warnings, *, code, line_number, sku, detail):
    """Agrega una advertencia normalizada para consumo uniforme del frontend."""
    warnings.append(
        {
            "code": code,
            "line": line_number,
            "sku": sku,
            "detail": detail,
        }
    )


def _registrar_warning_servicio_operativo(*, warnings, line_number, sku):
    """Advierte cuando una fila de servicio informa datos operativos que seran ignorados."""
    _append_warning(
        warnings,
        code="SERVICIO_CON_CAMPOS_INVENTARIO",
        line_number=line_number,
        sku=sku,
        detail="Los campos de inventario informados para un servicio se ignoraran automaticamente.",
    )


def _registrar_warning_precio_referencia_cero(*, warnings, line_number, sku):
    """Advierte cuando un producto activo queda con precio comercial en cero."""
    _append_warning(
        warnings,
        code="PRECIO_REFERENCIA_CERO",
        line_number=line_number,
        sku=sku,
        detail="El producto activo se importara con precio de referencia 0.",
    )


def _registrar_warning_sin_categoria(*, warnings, line_number, sku):
    """Advierte sobre productos activos sin categoria asignada."""
    _append_warning(
        warnings,
        code="PRODUCTO_SIN_CATEGORIA",
        line_number=line_number,
        sku=sku,
        detail="El producto activo quedara sin categoria.",
    )


def _registrar_warning_sin_impuesto(*, warnings, line_number, sku):
    """Advierte sobre productos activos sin impuesto asignado."""
    _append_warning(
        warnings,
        code="PRODUCTO_SIN_IMPUESTO",
        line_number=line_number,
        sku=sku,
        detail="El producto activo quedara sin impuesto.",
    )


def _registrar_warning_categoria_creada(*, warnings, line_number, sku, categoria_name):
    """Advierte la creacion implicita de una categoria durante la importacion."""
    _append_warning(
        warnings,
        code="CATEGORIA_CREADA_IMPLICITAMENTE",
        line_number=line_number,
        sku=sku,
        detail=f"Se creara la categoria '{categoria_name}' porque no existe en la empresa activa.",
    )


def _registrar_warning_impuesto_creado(*, warnings, line_number, sku, impuesto_name):
    """Advierte la creacion implicita de un impuesto durante la importacion."""
    _append_warning(
        warnings,
        code="IMPUESTO_CREADO_IMPLICITAMENTE",
        line_number=line_number,
        sku=sku,
        detail=f"Se creara el impuesto '{impuesto_name}' porque no existe en la empresa activa.",
    )


def _registrar_resumen_importacion(*, empresa, user, payload):
    """Registra auditoría y eventos de integración para la carga masiva de productos."""
    DomainEventService.record_event(
        empresa=empresa,
        aggregate_type="ProductoBulkImport",
        aggregate_id=empresa.id,
        event_type="productos.bulk_import.finalizado",
        payload=payload,
        meta={"source": "productos.bulk_import_service"},
        idempotency_key=f"productos-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}:{payload.get('warnings') or 0}",
        usuario=user,
    )
    OutboxService.enqueue(
        empresa=empresa,
        topic="productos.bulk_import",
        event_name="productos.bulk_import.finalizado",
        payload=payload,
        usuario=user,
        dedup_key=f"productos-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}:{payload.get('warnings') or 0}",
    )
    AuditoriaService.registrar_evento(
        empresa=empresa,
        usuario=user,
        module_code="PRODUCTOS",
        action_code="CREAR",
        event_type="PRODUCTOS_BULK_IMPORT",
        entity_type="PRODUCTO",
        summary="Carga masiva de productos ejecutada.",
        severity=AuditSeverity.INFO,
        changes={
            "registros_creados": [0, int(payload["created"])],
            "registros_actualizados": [0, int(payload["updated"])],
            "filas_con_error": [0, int(payload["errors"])],
            "filas_con_advertencia": [0, int(payload.get("warnings") or 0)],
        },
        payload=payload,
        source="productos.bulk_import_service",
        idempotency_key=f"audit:productos-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}:{payload.get('warnings') or 0}",
    )


def bulk_import_productos(*, uploaded_file, user, empresa, dry_run=False):
    """Importa productos desde CSV resolviendo catálogo relacionado dentro de la empresa activa."""
    empresa = _resolve_import_empresa(user, empresa)
    _ensure_admin_user(user, empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["nombre", "sku"],
    )

    if any("stock_actual" in row for _line, row in rows):
        raise BusinessRuleError(
            "La columna stock_actual ya no esta soportada. Gestione el stock desde inventario.",
            error_code="BULK_IMPORT_STOCK_ACTUAL_NO_SOPORTADO",
        )

    sku_candidates = []
    for _line, row in rows:
        sku_value = str(row.get("sku") or "").strip()
        if sku_value:
            sku_candidates.append(normalize_sku(sku_value))

    existing_products = {
        producto.sku: producto
        for producto in Producto.all_objects.filter(empresa=empresa, sku__in=sku_candidates)
    }

    categorias = {
        _normalize_name(categoria.nombre): categoria
        for categoria in Categoria.all_objects.filter(empresa=empresa)
    }
    impuestos = {
        _normalize_name(impuesto.nombre): impuesto
        for impuesto in Impuesto.all_objects.filter(empresa=empresa)
    }
    monedas = {}
    for moneda in Moneda.all_objects.filter(empresa=empresa):
        monedas[_normalize_name(moneda.codigo)] = moneda
        monedas[_normalize_name(moneda.nombre)] = moneda

    created = 0
    updated = 0
    errors = []
    warnings = []

    with bulk_import_execution_context(dry_run=dry_run):
        for line_number, row in rows:
            try:
                existing = existing_products.get(normalize_sku(str(row.get("sku") or "").strip()))
                nombre = str(row.get("nombre") or "").strip()
                if not nombre:
                    raise BusinessRuleError("El nombre es obligatorio.")

                sku_raw = str(row.get("sku") or "").strip()
                if not sku_raw:
                    raise BusinessRuleError("El SKU es obligatorio.")
                sku = normalize_sku(sku_raw)

                tipo = str(row.get("tipo") or TipoProducto.PRODUCTO).strip().upper() or TipoProducto.PRODUCTO
                if tipo not in {TipoProducto.PRODUCTO, TipoProducto.SERVICIO}:
                    raise BusinessRuleError("Tipo invalido. Use PRODUCTO o SERVICIO.")

                categoria = None
                categoria_name = _normalize_name(row.get("categoria"))
                if categoria_name:
                    categoria, categoria_created = _get_or_create_categoria(
                        categoria_name=categoria_name,
                        categorias=categorias,
                        empresa=empresa,
                        user=user,
                    )
                    if categoria_created:
                        _registrar_warning_categoria_creada(
                            warnings=warnings,
                            line_number=line_number,
                            sku=sku,
                            categoria_name=categoria_name,
                        )

                impuesto = None
                impuesto_name = _normalize_name(row.get("impuesto"))
                if impuesto_name:
                    impuesto, impuesto_created = _get_or_create_impuesto(
                        impuesto_name=impuesto_name,
                        impuestos=impuestos,
                        empresa=empresa,
                        user=user,
                    )
                    if impuesto_created:
                        _registrar_warning_impuesto_creado(
                            warnings=warnings,
                            line_number=line_number,
                            sku=sku,
                            impuesto_name=impuesto_name,
                        )

                moneda = existing.moneda if existing else None
                moneda_raw = row.get("moneda")
                if str(moneda_raw or "").strip():
                    moneda = _resolve_moneda(
                        raw_value=moneda_raw,
                        monedas=monedas,
                        empresa=empresa,
                    )

                precio_referencia = _to_decimal(row.get("precio_referencia"), default=Decimal("0"))
                precio_costo = _to_decimal(row.get("precio_costo"), default=Decimal("0"))
                stock_minimo = _to_decimal(row.get("stock_minimo"), default=Decimal("0"))
                maneja_inventario = _to_bool(row.get("maneja_inventario"), default=True)
                permite_decimales = _to_bool(
                    row.get("permite_decimales"),
                    default=getattr(existing, "permite_decimales", True),
                )
                usa_lotes = _to_bool(row.get("usa_lotes"), default=False)
                usa_series = _to_bool(row.get("usa_series"), default=False)
                usa_vencimiento = _to_bool(row.get("usa_vencimiento"), default=False)
                activo = _to_bool(row.get("activo"), default=True)
                servicio_con_campos_operativos = (
                    tipo == TipoProducto.SERVICIO
                    and (
                        maneja_inventario
                        or stock_minimo > Decimal("0")
                        or usa_lotes
                        or usa_series
                        or usa_vencimiento
                    )
                )

                unidad_medida = str(
                    row.get("unidad_medida")
                    or getattr(existing, "unidad_medida", UnidadMedida.UNIDAD)
                ).strip().upper()
                if unidad_medida not in {choice for choice, _label in UnidadMedida.choices}:
                    raise BusinessRuleError("Unidad de medida invalida.")

                if tipo == TipoProducto.SERVICIO:
                    maneja_inventario = False
                    stock_minimo = Decimal("0")
                    usa_lotes = False
                    usa_series = False
                    usa_vencimiento = False

                if usa_series:
                    usa_lotes = True
                    permite_decimales = False

                if servicio_con_campos_operativos:
                    _registrar_warning_servicio_operativo(
                        warnings=warnings,
                        line_number=line_number,
                        sku=sku,
                    )

                if activo and categoria is None:
                    _registrar_warning_sin_categoria(
                        warnings=warnings,
                        line_number=line_number,
                        sku=sku,
                    )

                if activo and impuesto is None:
                    _registrar_warning_sin_impuesto(
                        warnings=warnings,
                        line_number=line_number,
                        sku=sku,
                    )

                if activo and precio_referencia == Decimal("0"):
                    _registrar_warning_precio_referencia_cero(
                        warnings=warnings,
                        line_number=line_number,
                        sku=sku,
                    )

                payload = {
                    "nombre": nombre,
                    "descripcion": str(row.get("descripcion") or "").strip(),
                    "sku": sku,
                    "tipo": tipo,
                    "categoria": categoria,
                    "impuesto": impuesto,
                    "moneda": moneda,
                    "precio_referencia": precio_referencia,
                    "precio_costo": precio_costo,
                    "unidad_medida": unidad_medida,
                    "permite_decimales": permite_decimales,
                    "maneja_inventario": maneja_inventario,
                    "stock_minimo": stock_minimo,
                    "usa_lotes": usa_lotes,
                    "usa_series": usa_series,
                    "usa_vencimiento": usa_vencimiento,
                    "activo": activo,
                }

                if existing:
                    # El costo del maestro no se corrige por carga masiva sobre productos existentes.
                    payload.pop("precio_costo", None)
                    ProductoService.actualizar_producto(
                        producto_id=existing.id,
                        empresa=empresa,
                        usuario=user,
                        data=payload,
                    )
                    updated += 1
                else:
                    producto = ProductoService.crear_producto(
                        empresa=empresa,
                        usuario=user,
                        data=payload,
                    )
                    existing_products[sku] = producto
                    created += 1
            except Exception as exc:  # pragma: no cover - defensive guard for row-level resilience
                errors.append(
                    {
                        "line": line_number,
                        "sku": row.get("sku") or "",
                        "detail": format_bulk_import_row_error(exc),
                    }
                )

        result = build_bulk_import_result(
            created=created,
            updated=updated,
            errors=errors,
            warnings=warnings,
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
            "warnings": len(warnings),
            "total_rows": len(rows),
            "successful_rows": created + updated,
        },
    )
    return result


def build_productos_bulk_template(*, user, empresa):
    """Construye la plantilla XLSX oficial para carga masiva de productos."""
    _ensure_admin_user(user, empresa)

    headers = [
        "nombre",
        "sku",
        "tipo",
        "descripcion",
        "categoria",
        "impuesto",
        "moneda",
        "precio_referencia",
        "precio_costo",
        "unidad_medida",
        "permite_decimales",
        "maneja_inventario",
        "stock_minimo",
        "usa_lotes",
        "usa_series",
        "usa_vencimiento",
        "activo",
    ]

    sample = [
        "Taladro Percutor 650W",
        "SKU-DEMO-001",
        "PRODUCTO",
        "Incluye maletin y brocas",
        "General",
        "IVA 19",
        "CLP",
        "49990",
        "32000",
        "UN",
        "NO",
        "SI",
        "4",
        "NO",
        "NO",
        "NO",
        "SI",
    ]

    instructions = [
        "MODULO PRODUCTOS: use esta plantilla solo para productos.",
        "Columnas obligatorias: nombre, sku.",
        "tipo permitido: PRODUCTO o SERVICIO.",
        "NO usar EMPRESA/PERSONA en esta plantilla.",
        "moneda debe existir previamente en la empresa activa (ej: CLP, USD).",
        "unidad_medida permitida: UN, KG, GR, LT, MT, M2, M3, CJ.",
        "permite_decimales, maneja_inventario, usa_lotes, usa_series, usa_vencimiento y activo: use SI o NO.",
        "stock_actual no se importa desde esta plantilla; el stock operativo se gestiona solo desde inventario.",
        "precio_costo solo se usa al crear productos nuevos; no actualiza costos de productos existentes.",
        "Si tipo=SERVICIO, maneja_inventario=NO y los campos operativos de stock quedan sin efecto.",
        "categoria e impuesto se resolveran por nombre dentro de la empresa activa.",
        "sku identifica un producto existente para actualizarlo; si no existe, se crea.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="Productos",
        template_title="Plantilla de importacion - Productos",
    )
