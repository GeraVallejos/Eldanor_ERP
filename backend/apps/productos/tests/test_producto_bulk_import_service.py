from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.exceptions import BusinessRuleError
from apps.core.models import UserEmpresa
from apps.inventario.models import StockProducto
from apps.productos.models import Categoria, Impuesto, Producto
from apps.productos.services.bulk_import_service import bulk_import_productos


def _build_csv(content_rows):
    header = "nombre,sku,tipo,categoria,impuesto,precio_referencia,precio_costo,maneja_inventario,activo"
    body = "\n".join(content_rows)
    return f"{header}\n{body}\n"


def test_bulk_import_resuelve_categoria_e_impuesto_sin_contexto_tenant(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_service_bulk_productos",
        email="admin_service_bulk_productos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)

    categoria = Categoria.all_objects.create(empresa=empresa, creado_por=user, nombre="GENERAL")
    impuesto = Impuesto.all_objects.create(empresa=empresa, creado_por=user, nombre="IVA 19", porcentaje="19")

    csv_content = _build_csv([
        "Producto con categoria,SKU-CAT-001,PRODUCTO,GENERAL,IVA 19,1500,1000,true,true",
    ])
    uploaded = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_productos(uploaded_file=uploaded, user=user, empresa=empresa)

    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []

    producto = Producto.all_objects.get(empresa=empresa, sku="SKU-CAT-001")
    assert producto.categoria_id == categoria.id
    assert producto.impuesto_id == impuesto.id
    assert str(producto.costo_promedio) in {"1000", "1000.0000"}


def test_bulk_import_crea_categoria_si_no_existe(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_service_bulk_productos_autocat",
        email="admin_service_bulk_productos_autocat@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)

    impuesto = Impuesto.all_objects.create(empresa=empresa, creado_por=user, nombre="IVA 19", porcentaje="19")

    csv_content = _build_csv([
        "Producto auto categoria,SKU-CAT-NEW-001,PRODUCTO,GENERAL,IVA 19,1990,1000,true,true",
    ])
    uploaded = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_productos(uploaded_file=uploaded, user=user, empresa=empresa)

    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []

    producto = Producto.all_objects.get(empresa=empresa, sku="SKU-CAT-NEW-001")
    assert producto.categoria is not None
    assert producto.categoria.nombre == "GENERAL"
    assert producto.impuesto_id == impuesto.id


def test_bulk_import_crea_impuesto_si_no_existe(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_service_bulk_productos_autoimp",
        email="admin_service_bulk_productos_autoimp@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)

    Categoria.all_objects.create(empresa=empresa, creado_por=user, nombre="GENERAL")

    csv_content = _build_csv([
        "Producto auto impuesto,SKU-IMP-NEW-001,PRODUCTO,GENERAL,IVA 19,2500,1300,true,true",
    ])
    uploaded = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_productos(uploaded_file=uploaded, user=user, empresa=empresa)

    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []

    producto = Producto.all_objects.get(empresa=empresa, sku="SKU-IMP-NEW-001")
    assert producto.impuesto is not None
    assert producto.impuesto.nombre == "IVA 19"
    assert str(producto.impuesto.porcentaje) in {"19", "19.00"}


def test_bulk_import_no_sincroniza_stock_operativo(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_service_bulk_productos_stock",
        email="admin_service_bulk_productos_stock@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)

    Categoria.all_objects.create(empresa=empresa, creado_por=user, nombre="GENERAL")
    Impuesto.all_objects.create(empresa=empresa, creado_por=user, nombre="IVA 19", porcentaje="19")

    csv_content = _build_csv([
        "Producto resumen,SKU-RES-001,PRODUCTO,GENERAL,IVA 19,5000,3000,true,true",
    ])
    uploaded = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")

    result = bulk_import_productos(uploaded_file=uploaded, user=user, empresa=empresa)

    assert result["created"] == 1
    assert result["errors"] == []

    producto = Producto.all_objects.get(empresa=empresa, sku="SKU-RES-001")
    stock = StockProducto.all_objects.filter(empresa=empresa, producto=producto).first()
    assert stock is None
    assert str(producto.stock_actual) in {"0", "0.00"}
    assert str(producto.costo_promedio) in {"3000", "3000.0000"}


def test_bulk_import_rechaza_columna_stock_actual(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_service_bulk_productos_columna_stock",
        email="admin_service_bulk_productos_columna_stock@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)

    csv_content = "\n".join([
        "nombre,sku,stock_actual",
        "Producto legacy,SKU-LEGACY-001,9",
    ]) + "\n"
    uploaded = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")

    try:
        bulk_import_productos(uploaded_file=uploaded, user=user, empresa=empresa)
    except BusinessRuleError as exc:
        assert exc.error_code == "BULK_IMPORT_STOCK_ACTUAL_NO_SOPORTADO"
        assert "stock_actual" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba rechazo explicito de la columna stock_actual.")
