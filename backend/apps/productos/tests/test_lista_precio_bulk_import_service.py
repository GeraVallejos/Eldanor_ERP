from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.auditoria.models import AuditEvent
from apps.core.models import DomainEvent, OutboxEvent, UserEmpresa
from apps.productos.models import ListaPrecio, ListaPrecioItem, Producto
from apps.productos.services.lista_precio_bulk_import_service import bulk_import_lista_precio_items
from apps.tesoreria.models import Moneda


def _build_csv(content_rows):
    header = "sku,precio,descuento_maximo"
    body = "\n".join(content_rows)
    return f"{header}\n{body}\n"


def _build_admin_user(*, empresa, username):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)
    return user


def test_bulk_import_lista_precio_crea_y_actualiza_items(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_service")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Norte",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )
    producto_existente = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto existente",
        sku="SKU-LISTA-001",
        precio_referencia=Decimal("15000"),
    )
    producto_nuevo = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto nuevo",
        sku="SKU-LISTA-002",
        precio_referencia=Decimal("18000"),
    )
    item = ListaPrecioItem.objects.create(
        empresa=empresa,
        creado_por=user,
        lista=lista,
        producto=producto_existente,
        precio=Decimal("14990"),
        descuento_maximo=Decimal("3"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-001,13990,8",
        "SKU-LISTA-002,17500,5",
    ])
    uploaded = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded,
        user=user,
        empresa=empresa,
    )

    assert result["created"] == 1
    assert result["updated"] == 1
    assert result["errors"] == []

    item.refresh_from_db()
    assert item.precio == Decimal("13990")
    assert item.descuento_maximo == Decimal("8")

    nuevo_item = ListaPrecioItem.all_objects.get(empresa=empresa, lista=lista, producto=producto_nuevo)
    assert nuevo_item.precio == Decimal("17500")
    assert nuevo_item.descuento_maximo == Decimal("5")

    assert DomainEvent.all_objects.filter(
        empresa=empresa,
        aggregate_type="ListaPrecioItem",
        aggregate_id=item.id,
        event_type="lista_precio_item.actualizado",
    ).exists()
    assert OutboxEvent.all_objects.filter(
        empresa=empresa,
        topic="productos.precios",
        event_name="lista_precio.bulk_import.finalizado",
    ).exists()
    assert AuditEvent.all_objects.filter(
        empresa=empresa,
        entity_type="LISTA_PRECIO",
        entity_id=str(lista.id),
        event_type="LISTA_PRECIO_BULK_IMPORT",
    ).exists()


def test_bulk_import_lista_precio_repetida_actualiza_sin_error(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_repeat")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Repeat",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )
    producto = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto repeat",
        sku="SKU-LISTA-REPEAT-001",
        precio_referencia=Decimal("15000"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-REPEAT-001,13990,8",
    ])
    uploaded_1 = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")
    uploaded_2 = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    first_result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded_1,
        user=user,
        empresa=empresa,
    )
    second_result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded_2,
        user=user,
        empresa=empresa,
    )

    assert first_result["created"] == 1
    assert first_result["updated"] == 0
    assert first_result["errors"] == []

    assert second_result["created"] == 0
    assert second_result["updated"] == 1
    assert second_result["errors"] == []

    item = ListaPrecioItem.all_objects.get(empresa=empresa, lista=lista, producto=producto)
    assert item.precio == Decimal("13990")
    assert item.descuento_maximo == Decimal("8")


def test_bulk_import_lista_precio_dry_run_repetida_no_marca_duplicado(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_repeat_preview")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Repeat Preview",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )
    producto = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto repeat preview",
        sku="SKU-LISTA-REPEAT-PREVIEW-001",
        precio_referencia=Decimal("15000"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-REPEAT-PREVIEW-001,13990,8",
    ])
    uploaded_apply = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")
    uploaded_preview = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded_apply,
        user=user,
        empresa=empresa,
    )
    result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded_preview,
        user=user,
        empresa=empresa,
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["created"] == 0
    assert result["updated"] == 1
    assert result["errors"] == []


def test_bulk_import_lista_precio_reporta_sku_inexistente_y_continua(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_errors")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Sur",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=50,
    )
    producto_valido = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto valido",
        sku="SKU-LISTA-OK-001",
        precio_referencia=Decimal("9900"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-OK-001,9500,0",
        "SKU-NO-EXISTE,1234,0",
    ])
    uploaded = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded,
        user=user,
        empresa=empresa,
    )

    assert result["created"] == 1
    assert result["updated"] == 0
    assert len(result["errors"]) == 1
    assert "SKU-NO-EXISTE" in result["errors"][0]["detail"]

    assert ListaPrecioItem.all_objects.filter(empresa=empresa, lista=lista, producto=producto_valido).exists()


def test_bulk_import_lista_precio_advierte_precios_cero(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_zero")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Cero",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )
    producto = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto sin precio",
        sku="SKU-LISTA-CERO-001",
        precio_referencia=Decimal("9900"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-CERO-001,0,0",
    ])
    uploaded = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded,
        user=user,
        empresa=empresa,
        dry_run=True,
    )

    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["code"] == "PRECIO_CERO"
    assert result["warnings"][0]["sku"] == "SKU-LISTA-CERO-001"


def test_bulk_import_lista_precio_formatea_errores_de_validacion(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_validation")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Validacion",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )
    Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto validacion",
        sku="SKU-LISTA-VALIDACION-001",
        precio_referencia=Decimal("9900"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-VALIDACION-001,12000,150",
    ])
    uploaded = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded,
        user=user,
        empresa=empresa,
        dry_run=True,
    )

    assert result["successful_rows"] == 0
    assert len(result["errors"]) == 1
    assert result["errors"][0]["detail"] == "descuento_maximo: El descuento maximo debe estar entre 0 y 100."


def test_bulk_import_lista_precio_dry_run_no_persiste_cambios(db, empresa):
    user = _build_admin_user(empresa=empresa, username="admin_lista_precio_bulk_preview")
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Mayorista Preview",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )
    producto = Producto.objects.create(
        empresa=empresa,
        creado_por=user,
        nombre="Producto preview",
        sku="SKU-LISTA-PREVIEW-001",
        precio_referencia=Decimal("11990"),
    )

    csv_content = _build_csv([
        "SKU-LISTA-PREVIEW-001,10990,4",
    ])
    uploaded = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_lista_precio_items(
        lista_id=lista.id,
        uploaded_file=uploaded,
        user=user,
        empresa=empresa,
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []
    assert not ListaPrecioItem.all_objects.filter(empresa=empresa, lista=lista, producto=producto).exists()
    assert not DomainEvent.all_objects.filter(
        empresa=empresa,
        aggregate_type="ListaPrecioBulkImport",
        aggregate_id=lista.id,
    ).exists()
    assert not AuditEvent.all_objects.filter(
        empresa=empresa,
        entity_type="LISTA_PRECIO",
        entity_id=str(lista.id),
        event_type="LISTA_PRECIO_BULK_IMPORT",
    ).exists()
