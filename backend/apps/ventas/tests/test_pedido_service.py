import pytest
from decimal import Decimal

from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.core.exceptions import BusinessRuleError, ConflictError
from apps.core.models import UserEmpresa
from apps.core.tenant import set_current_empresa, set_current_user
from apps.productos.models import Impuesto, Producto
from apps.ventas.models import EstadoPedidoVenta, PedidoVenta, PedidoVentaItem
from apps.ventas.services import PedidoVentaService


@pytest.fixture
def usuario_owner(db, empresa):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_pv",
        email="owner_pv@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def cliente(db, empresa):
    set_current_empresa(empresa)
    contacto = Contacto.objects.create(nombre="Cliente PV", email="clientepv@test.com")
    c = Cliente.objects.create(contacto=contacto)
    set_current_empresa(None)
    return c


@pytest.fixture
def impuesto(db, empresa):
    set_current_empresa(empresa)
    imp = Impuesto.objects.create(nombre="IVA", porcentaje=Decimal("19"))
    set_current_empresa(None)
    return imp


@pytest.fixture
def producto(db, empresa, impuesto):
    set_current_empresa(empresa)
    p = Producto.objects.create(
        nombre="Prod Test",
        sku="SKU-PV001",
        precio_referencia=Decimal("1000"),
        maneja_inventario=False,
        impuesto=impuesto,
    )
    set_current_empresa(None)
    return p


@pytest.mark.django_db
class TestPedidoVentaService:

    def test_crear_pedido_asigna_folio(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        assert pedido.numero is not None
        assert pedido.numero.startswith("PV-") or len(pedido.numero) > 0
        assert pedido.estado == EstadoPedidoVenta.BORRADOR

    def test_crear_pedido_genera_numero_unico(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        p1 = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        p2 = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-02"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        assert p1.numero != p2.numero

    def test_confirmar_pedido_sin_items_lanza_error(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        with pytest.raises(BusinessRuleError):
            PedidoVentaService.confirmar_pedido(
                pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
            )

    def test_confirmar_pedido_con_items_sin_inventario(self, empresa, usuario_owner, cliente, producto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
        )
        pedido_confirmado = PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
        )
        assert pedido_confirmado.estado == EstadoPedidoVenta.CONFIRMADO

    def test_confirmar_pedido_dos_veces_lanza_conflict(self, empresa, usuario_owner, cliente, producto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
        )
        PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
        )
        with pytest.raises(ConflictError):
            PedidoVentaService.confirmar_pedido(
                pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
            )

    def test_anular_pedido_borrador(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        pedido_anulado = PedidoVentaService.anular_pedido(
            pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner, motivo="test"
        )
        assert pedido_anulado.estado == EstadoPedidoVenta.ANULADO

    def test_anular_pedido_facturado_lanza_conflict(self, empresa, usuario_owner, cliente, producto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        # Forzar estado FACTURADO directamente
        pedido.estado = EstadoPedidoVenta.FACTURADO
        pedido.save(update_fields=["estado"])
        with pytest.raises(ConflictError):
            PedidoVentaService.anular_pedido(
                pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
            )

    def test_eliminar_pedido_borrador(self, empresa, usuario_owner, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        pedido_id = pedido.id
        PedidoVentaService.eliminar_pedido(
            pedido_id=pedido_id, empresa=empresa, usuario=usuario_owner
        )
        assert not PedidoVenta.all_objects.filter(pk=pedido_id).exists()

    def test_eliminar_pedido_confirmado_lanza_conflict(self, empresa, usuario_owner, cliente, producto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
        )
        PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
        )
        with pytest.raises(ConflictError):
            PedidoVentaService.eliminar_pedido(
                pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
            )

    def test_duplicar_pedido(self, empresa, usuario_owner, cliente, producto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("1500"),
        )
        PedidoVentaService.recalcular_totales(pedido=pedido)

        nuevo = PedidoVentaService.duplicar_pedido(
            pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
        )
        assert nuevo.numero != pedido.numero
        assert nuevo.estado == EstadoPedidoVenta.BORRADOR
        assert PedidoVentaItem.all_objects.filter(pedido_venta=nuevo).count() == 1

    def test_recalcular_totales(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("1000"),
            descuento=Decimal("0"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        PedidoVentaService.recalcular_totales(pedido=pedido)
        pedido.refresh_from_db()
        assert pedido.subtotal == Decimal("2000.00")
        assert pedido.impuestos == Decimal("380.00")
        assert pedido.total == Decimal("2380.00")

    def test_historial_registrado_en_confirmacion(self, empresa, usuario_owner, cliente, producto):
        from apps.ventas.models import TipoDocumentoVenta, VentaHistorial
        set_current_empresa(empresa)
        set_current_user(usuario_owner)
        pedido = PedidoVentaService.crear_pedido(
            datos={"cliente": cliente, "fecha_emision": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_owner,
        )
        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
        )
        PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id, empresa=empresa, usuario=usuario_owner
        )
        historial = VentaHistorial.all_objects.filter(
            empresa=empresa,
            tipo_documento=TipoDocumentoVenta.PEDIDO,
            documento_id=pedido.id,
        )
        assert historial.exists()
        assert historial.first().estado_nuevo == EstadoPedidoVenta.CONFIRMADO
