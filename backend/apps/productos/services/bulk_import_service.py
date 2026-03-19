from decimal import Decimal, InvalidOperation
import re

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.core.models import Moneda
from apps.core.roles import RolUsuario
from apps.core.services import DomainEventService, OutboxService
from apps.core.services.csv_import import parse_csv_upload
from apps.core.services.xlsx_template import build_xlsx_template
from apps.inventario.models import Bodega, StockProducto
from apps.productos.models import Categoria, Impuesto, Producto, TipoProducto, UnidadMedida
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
    categoria = categorias.get(categoria_name)
    if categoria:
        return categoria

    categoria = Categoria.all_objects.filter(
        empresa=empresa,
        nombre__iexact=categoria_name,
    ).first()
    if categoria:
        categorias[categoria_name] = categoria
        return categoria

    categoria = Categoria(empresa=empresa, creado_por=user, nombre=categoria_name)
    categoria.save()
    categorias[categoria_name] = categoria
    return categoria


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
    impuesto = impuestos.get(impuesto_name)
    if impuesto:
        return impuesto

    impuesto = Impuesto.all_objects.filter(
        empresa=empresa,
        nombre__iexact=impuesto_name,
    ).first()
    if impuesto:
        impuestos[impuesto_name] = impuesto
        return impuesto

    porcentaje = _extract_impuesto_porcentaje(impuesto_name)
    if porcentaje is not None:
        impuesto_by_pct = Impuesto.all_objects.filter(
            empresa=empresa,
            porcentaje=porcentaje,
        ).first()
        if impuesto_by_pct:
            impuestos[impuesto_name] = impuesto_by_pct
            return impuesto_by_pct
    else:
        porcentaje = Decimal("19")

    impuesto = Impuesto(empresa=empresa, creado_por=user, nombre=impuesto_name, porcentaje=porcentaje)
    try:
        impuesto.save()
    except Exception:
        # If percentage uniqueness collides with an existing tax config, reuse that tax.
        fallback = Impuesto.all_objects.filter(empresa=empresa, porcentaje=porcentaje).first()
        if not fallback:
            raise
        impuesto = fallback

    impuestos[impuesto_name] = impuesto
    return impuesto


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


def _sync_stock_producto(*, producto, empresa, user, precio_costo):
    if not producto.maneja_inventario:
        return

    bodega_default, _ = Bodega.all_objects.get_or_create(
        empresa=empresa,
        nombre="Principal",
        defaults={"activa": True, "creado_por": user},
    )

    stock = Decimal(producto.stock_actual or 0).quantize(Decimal("0.01"))
    costo_base = Decimal(precio_costo or 0)
    valor_stock = (stock * costo_base).quantize(Decimal("0.01"))

    stock_obj, _ = StockProducto.all_objects.get_or_create(
        empresa=empresa,
        producto=producto,
        bodega=bodega_default,
        defaults={
            "creado_por": user,
            "stock": stock,
            "valor_stock": valor_stock,
        },
    )
    if stock_obj.stock != stock or stock_obj.valor_stock != valor_stock:
        stock_obj.stock = stock
        stock_obj.valor_stock = valor_stock
        stock_obj.save(update_fields=["stock", "valor_stock"])


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


def _registrar_resumen_importacion(*, empresa, user, payload):
    """Registra auditoría y eventos de integración para la carga masiva de productos."""
    DomainEventService.record_event(
        empresa=empresa,
        aggregate_type="ProductoBulkImport",
        aggregate_id=empresa.id,
        event_type="productos.bulk_import.finalizado",
        payload=payload,
        meta={"source": "productos.bulk_import_service"},
        idempotency_key=f"productos-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
        usuario=user,
    )
    OutboxService.enqueue(
        empresa=empresa,
        topic="productos.bulk_import",
        event_name="productos.bulk_import.finalizado",
        payload=payload,
        usuario=user,
        dedup_key=f"productos-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
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
        },
        payload=payload,
        source="productos.bulk_import_service",
        idempotency_key=f"audit:productos-bulk-import:{payload['total_rows']}:{payload['successful_rows']}:{payload['errors']}",
    )


def bulk_import_productos(*, uploaded_file, user, empresa):
    """Importa productos desde CSV resolviendo catálogo relacionado dentro de la empresa activa."""
    empresa = _resolve_import_empresa(user, empresa)
    _ensure_admin_user(user, empresa)

    rows = parse_csv_upload(
        uploaded_file,
        required_headers=["nombre", "sku"],
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
                categoria = _get_or_create_categoria(
                    categoria_name=categoria_name,
                    categorias=categorias,
                    empresa=empresa,
                    user=user,
                )

            impuesto = None
            impuesto_name = _normalize_name(row.get("impuesto"))
            if impuesto_name:
                impuesto = _get_or_create_impuesto(
                    impuesto_name=impuesto_name,
                    impuestos=impuestos,
                    empresa=empresa,
                    user=user,
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
            stock_actual = _to_decimal(row.get("stock_actual"), default=Decimal("0"))
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

            unidad_medida = str(
                row.get("unidad_medida")
                or getattr(existing, "unidad_medida", UnidadMedida.UNIDAD)
            ).strip().upper()
            if unidad_medida not in {choice for choice, _label in UnidadMedida.choices}:
                raise BusinessRuleError("Unidad de medida invalida.")

            if tipo == TipoProducto.SERVICIO:
                maneja_inventario = False
                stock_actual = Decimal("0")
                stock_minimo = Decimal("0")
                usa_lotes = False
                usa_series = False
                usa_vencimiento = False

            if usa_series:
                usa_lotes = True
                permite_decimales = False

            payload = {
                "empresa": empresa,
                "creado_por": user,
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
                "stock_actual": stock_actual,
                "stock_minimo": stock_minimo,
                "usa_lotes": usa_lotes,
                "usa_series": usa_series,
                "usa_vencimiento": usa_vencimiento,
                "activo": activo,
            }

            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                existing.save()
                _sync_stock_producto(
                    producto=existing,
                    empresa=empresa,
                    user=user,
                    precio_costo=precio_costo,
                )
                updated += 1
            else:
                producto = Producto(**payload)
                producto.save()
                _sync_stock_producto(
                    producto=producto,
                    empresa=empresa,
                    user=user,
                    precio_costo=precio_costo,
                )
                existing_products[sku] = producto
                created += 1
        except Exception as exc:  # pragma: no cover - defensive guard for row-level resilience
            errors.append(
                {
                    "line": line_number,
                    "sku": row.get("sku") or "",
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
        "stock_actual",
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
        "false",
        "true",
        "12",
        "4",
        "false",
        "false",
        "false",
        "true",
    ]

    instructions = [
        "MODULO PRODUCTOS: use esta plantilla solo para productos.",
        "Columnas obligatorias: nombre, sku.",
        "tipo permitido: PRODUCTO o SERVICIO.",
        "NO usar EMPRESA/PERSONA en esta plantilla.",
        "moneda debe existir previamente en la empresa activa (ej: CLP, USD).",
        "unidad_medida permitida: UN, KG, GR, LT, MT, M2, M3, CJ.",
        "permite_decimales, maneja_inventario, usa_lotes, usa_series, usa_vencimiento y activo: true/false.",
        "Si tipo=SERVICIO, stock_actual se fuerza a 0 y maneja_inventario=false.",
        "categoria e impuesto se resolveran por nombre dentro de la empresa activa.",
        "sku identifica un producto existente para actualizarlo; si no existe, se crea.",
    ]

    return build_xlsx_template(
        headers=headers,
        sample_row=sample,
        instructions=instructions,
        sheet_name="Productos",
    )
