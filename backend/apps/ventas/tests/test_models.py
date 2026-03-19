import pytest
from decimal import Decimal

from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.core.models import UserEmpresa
from apps.core.tenant import set_current_empresa, set_current_user
from apps.productos.models import Impuesto, Producto
from apps.ventas.models import (
    EstadoGuiaDespacho,
    EstadoPedidoVenta,
    GuiaDespacho,
    GuiaDespachoItem,
    PedidoVenta,
    PedidoVentaItem,
)


@pytest.fixture
def usuario_owner(db, empresa):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_ventas",
        email="owner_ventas@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def cliente(db, empresa):
    set_current_empresa(empresa)
    contacto = Contacto.objects.create(nombre="Cliente Test", email="cliente@test.com")
    c = Cliente.objects.create(contacto=contacto)
    set_current_empresa(None)
    return c


@pytest.fixture
def impuesto(db, empresa):
    set_current_empresa(empresa)
    imp = Impuesto.objects.create(nombre="IVA 19%", porcentaje=Decimal("19"))
    set_current_empresa(None)
    return imp


@pytest.fixture
def producto(db, empresa, impuesto):
    set_current_empresa(empresa)
    p = Producto.objects.create(
        nombre="Producto Test",
        sku="PROD-001",
        precio_referencia=Decimal("1000"),
        maneja_inventario=True,
        stock_actual=Decimal("50"),
        impuesto=impuesto,
    )
    set_current_empresa(None)
    return p


@pytest.mark.django_db
class TestPedidoVentaModel:

    def test_str(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVenta.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="PV-00001",
            cliente=cliente,
            estado=EstadoPedidoVenta.BORRADOR,
            fecha_emision="2026-01-01",
        )
        assert str(pedido) == "PV PV-00001"

    def test_descuento_invalido_lanza_validation_error(self, empresa, usuario_owner, cliente):
        from django.core.exceptions import ValidationError
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVenta(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="PV-99",
            cliente=cliente,
            fecha_emision="2026-01-01",
            descuento=Decimal("110"),
        )
        with pytest.raises(ValidationError):
            pedido.full_clean()

    def test_fecha_entrega_anterior_lanza_error(self, empresa, usuario_owner, cliente):
        from django.core.exceptions import ValidationError
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVenta(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="PV-98",
            cliente=cliente,
            fecha_emision="2026-05-10",
            fecha_entrega="2026-05-01",
        )
        with pytest.raises(ValidationError):
            pedido.full_clean()


@pytest.mark.django_db
class TestPedidoVentaItemModel:

    def test_calcular_totales_con_descuento_e_impuesto(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVenta.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="PV-00010",
            cliente=cliente,
            estado=EstadoPedidoVenta.BORRADOR,
            fecha_emision="2026-01-01",
        )
        item = PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("1000"),
            descuento=Decimal("10"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        # bruto = 2000, descuento 10% = 200, subtotal = 1800, iva 19% = 342, total = 2142
        assert item.subtotal == Decimal("1800.00")
        assert item.total == Decimal("2142.00")

    def test_descripcion_auto_desde_producto(self, empresa, usuario_owner, cliente, producto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVenta.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="PV-00011",
            cliente=cliente,
            estado=EstadoPedidoVenta.BORRADOR,
            fecha_emision="2026-01-01",
        )
        item = PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("500"),
        )
        assert item.descripcion == producto.nombre


@pytest.mark.django_db
class TestGuiaDespachoModel:

    def test_str(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        guia = GuiaDespacho.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="GD-00001",
            cliente=cliente,
            estado=EstadoGuiaDespacho.BORRADOR,
            fecha_despacho="2026-01-01",
        )
        assert str(guia) == "GD GD-00001"

    def test_item_calcula_sin_descuento(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        guia = GuiaDespacho.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            numero="GD-00002",
            cliente=cliente,
            estado=EstadoGuiaDespacho.BORRADOR,
            fecha_despacho="2026-01-01",
        )
        item = GuiaDespachoItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            guia_despacho=guia,
            producto=producto,
            cantidad=Decimal("3"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        assert item.subtotal == Decimal("3000.00")
        assert item.total == Decimal("3570.00")
