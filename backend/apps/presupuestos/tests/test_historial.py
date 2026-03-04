import pytest
from decimal import Decimal
from apps.presupuestos.models import Presupuesto, EstadoPresupuesto
from apps.productos.models import Producto, Impuesto

@pytest.fixture
def usuario_admin(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(username="admin_test", email="admin@test.com", password="password123")

@pytest.fixture
def empresa(db):
    from apps.core.models import Empresa
    return Empresa.objects.create(nombre="EMPRESA TEST")

@pytest.fixture
def cliente(db, empresa):
    from apps.contactos.models import Cliente
    return Cliente.objects.create(nombre="CLIENTE TEST", empresa=empresa)

@pytest.fixture
def impuesto_iva(db, empresa):
    return Impuesto.objects.create(nombre="IVA", porcentaje=Decimal("19.00"), empresa=empresa)

@pytest.fixture
def producto_con_iva(db, empresa, impuesto_iva):
    return Producto.objects.create(
        nombre="Producto Test", 
        sku="TEST-01",
        precio_venta=Decimal("100.00"), 
        impuesto=impuesto_iva,
        empresa=empresa,
        maneja_inventario=True,
        stock_actual=Decimal("100.00")
    )

@pytest.fixture
def presupuesto_borrador(db, empresa, usuario_admin, cliente):
    return Presupuesto.objects.create(
        numero=100,
        cliente=cliente,
        empresa=empresa,
        fecha="2026-01-01",
        creado_por=usuario_admin,
        estado=EstadoPresupuesto.BORRADOR
    )