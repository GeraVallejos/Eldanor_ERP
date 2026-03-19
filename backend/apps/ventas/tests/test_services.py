import pytest
from decimal import Decimal

from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.core.models import DomainEvent, OutboxEvent, UserEmpresa
from apps.core.models.cartera import CuentaPorCobrar
from apps.core.tenant import set_current_empresa, set_current_user
from apps.documentos.models import EstadoIntegracionTributaria
from apps.productos.models import Impuesto, Producto
from apps.ventas.models import (
    EstadoFacturaVenta,
    EstadoGuiaDespacho,
    EstadoNotaCreditoVenta,
    EstadoPedidoVenta,
    FacturaVenta,
    FacturaVentaItem,
    GuiaDespacho,
    GuiaDespachoItem,
    NotaCreditoVenta,
    NotaCreditoVentaItem,
    PedidoVenta,
    PedidoVentaItem,
    TipoNotaCreditoVenta,
)
from apps.ventas.services import (
    FacturaVentaService,
    GuiaDespachoService,
    NotaCreditoVentaService,
    PedidoVentaService,
)


@pytest.fixture
def usuario_owner(db, empresa):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_ventas_service",
        email="owner_ventas_service@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def cliente(db, empresa):
    set_current_empresa(empresa)
    contacto = Contacto.objects.create(nombre="Cliente Service", email="cliente_service@test.com")
    c = Cliente.objects.create(contacto=contacto, dias_credito=30)
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
        nombre="Producto Service",
        sku="PROD-SVC-001",
        precio_referencia=Decimal("1000"),
        maneja_inventario=True,
        stock_actual=Decimal("100"),
        impuesto=impuesto,
    )
    set_current_empresa(None)
    return p


def _crear_pedido_base(empresa, usuario_owner, cliente):
    set_current_empresa(empresa)
    set_current_user(usuario_owner)
    return PedidoVentaService.crear_pedido(
        datos={
            "cliente": cliente,
            "fecha_emision": "2026-01-01",
            "observaciones": "Pedido base",
        },
        empresa=empresa,
        usuario=usuario_owner,
    )


@pytest.mark.django_db
class TestPedidoVentaService:

    def test_crear_confirmar_y_anular_pedido(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)

        pedido = _crear_pedido_base(empresa, usuario_owner, cliente)
        assert pedido.numero
        assert pedido.estado == EstadoPedidoVenta.BORRADOR

        PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        PedidoVentaService.recalcular_totales(pedido=pedido)
        pedido.refresh_from_db()
        assert pedido.total == Decimal("2380.00")

        pedido = PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id,
            empresa=empresa,
            usuario=usuario_owner,
        )
        assert pedido.estado == EstadoPedidoVenta.CONFIRMADO

        pedido = PedidoVentaService.anular_pedido(
            pedido_id=pedido.id,
            empresa=empresa,
            usuario=usuario_owner,
            motivo="Cliente desistió",
        )
        assert pedido.estado == EstadoPedidoVenta.ANULADO


@pytest.mark.django_db
class TestGuiaDespachoService:

    def test_confirmar_y_anular_guia(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)

        pedido = _crear_pedido_base(empresa, usuario_owner, cliente)
        pedido_item = PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        PedidoVentaService.recalcular_totales(pedido=pedido)
        PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id,
            empresa=empresa,
            usuario=usuario_owner,
        )

        guia = GuiaDespachoService.crear_guia(
            datos={
                "cliente": cliente,
                "pedido_venta": pedido,
                "fecha_despacho": "2026-01-02",
            },
            empresa=empresa,
            usuario=usuario_owner,
        )
        GuiaDespachoItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            guia_despacho=guia,
            pedido_item=pedido_item,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        GuiaDespachoService.recalcular_totales(guia=guia)

        guia = GuiaDespachoService.confirmar_guia(
            guia_id=guia.id,
            empresa=empresa,
            usuario=usuario_owner,
            bodega_id=None,
        )
        assert guia.estado == EstadoGuiaDespacho.CONFIRMADA

        guia = GuiaDespachoService.anular_guia(
            guia_id=guia.id,
            empresa=empresa,
            usuario=usuario_owner,
            bodega_id=None,
            motivo="Error de despacho",
        )
        assert guia.estado == EstadoGuiaDespacho.ANULADA


@pytest.mark.django_db
class TestFacturaNotaCreditoServices:

    def test_emitir_factura_crea_cxc_y_anular_genera_nc(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)

        pedido = _crear_pedido_base(empresa, usuario_owner, cliente)

        factura = FacturaVentaService.crear_factura(
            datos={
                "cliente": cliente,
                "pedido_venta": pedido,
                "fecha_emision": "2026-01-03",
                "fecha_vencimiento": "2026-02-02",
            },
            empresa=empresa,
            usuario=usuario_owner,
        )
        FacturaVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            factura_venta=factura,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            descuento=Decimal("0"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        FacturaVentaService.recalcular_totales(factura=factura)

        factura = FacturaVentaService.emitir_factura(
            factura_id=factura.id,
            empresa=empresa,
            usuario=usuario_owner,
        )
        assert factura.estado == EstadoFacturaVenta.EMITIDA
        assert factura.estado_tributario == EstadoIntegracionTributaria.EN_COLA

        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_id=factura.id,
            event_type="tributario.factura_venta.solicitado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="sii.dte",
            event_name="factura_venta.solicitar_emision",
        ).exists()

        referencia = f"FV-{factura.numero}-{str(factura.id)[:8]}"
        cxc = CuentaPorCobrar.all_objects.filter(empresa=empresa, referencia=referencia).first()
        assert cxc is not None
        assert cxc.monto_total == factura.total

        factura = FacturaVentaService.anular_factura(
            factura_id=factura.id,
            empresa=empresa,
            usuario=usuario_owner,
            motivo="Anulación de prueba",
        )
        assert factura.estado == EstadoFacturaVenta.ANULADA

        nc = NotaCreditoVenta.all_objects.filter(
            empresa=empresa,
            factura_origen=factura,
            tipo=TipoNotaCreditoVenta.ANULACION,
        ).first()
        assert nc is not None
        assert nc.estado == EstadoNotaCreditoVenta.EMITIDA

    def test_emitir_nota_credito_manual_aplica_saldo_cxc(
        self, empresa, usuario_owner, cliente, producto, impuesto
    ):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)

        factura = FacturaVentaService.crear_factura(
            datos={
                "cliente": cliente,
                "fecha_emision": "2026-01-03",
                "fecha_vencimiento": "2026-02-02",
            },
            empresa=empresa,
            usuario=usuario_owner,
        )
        f_item = FacturaVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            factura_venta=factura,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("1000"),
            descuento=Decimal("0"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        FacturaVentaService.recalcular_totales(factura=factura)
        factura = FacturaVentaService.emitir_factura(
            factura_id=factura.id, empresa=empresa, usuario=usuario_owner
        )

        nota = NotaCreditoVentaService.crear_nota_credito(
            datos={
                "factura_origen": factura,
                "cliente": cliente,
                "tipo": TipoNotaCreditoVenta.DESCUENTO,
                "fecha_emision": "2026-01-10",
                "motivo": "Descuento comercial",
            },
            empresa=empresa,
            usuario=usuario_owner,
        )

        NotaCreditoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            nota_credito=nota,
            factura_item=f_item,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        NotaCreditoVentaService.recalcular_totales(nota=nota)

        nota = NotaCreditoVentaService.emitir_nota_credito(
            nota_id=nota.id,
            empresa=empresa,
            usuario=usuario_owner,
        )
        assert nota.estado == EstadoNotaCreditoVenta.EMITIDA
        assert nota.estado_tributario == EstadoIntegracionTributaria.EN_COLA
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_id=nota.id,
            event_type="tributario.nota_credito_venta.solicitado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="sii.dte",
            event_name="nota_credito_venta.solicitar_emision",
        ).exists()

        referencia = f"FV-{factura.numero}-{str(factura.id)[:8]}"
        cxc = CuentaPorCobrar.all_objects.get(empresa=empresa, referencia=referencia)
        assert cxc.saldo < cxc.monto_total

    def test_confirmar_guia_encola_integracion_tributaria(self, empresa, usuario_owner, cliente, producto, impuesto):
        set_current_empresa(empresa)
        set_current_user(usuario_owner)

        pedido = _crear_pedido_base(empresa, usuario_owner, cliente)
        pedido_item = PedidoVentaItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            pedido_venta=pedido,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        PedidoVentaService.recalcular_totales(pedido=pedido)
        PedidoVentaService.confirmar_pedido(
            pedido_id=pedido.id,
            empresa=empresa,
            usuario=usuario_owner,
        )

        guia = GuiaDespachoService.crear_guia(
            datos={
                "cliente": cliente,
                "pedido_venta": pedido,
                "fecha_despacho": "2026-01-02",
            },
            empresa=empresa,
            usuario=usuario_owner,
        )
        GuiaDespachoItem.all_objects.create(
            empresa=empresa,
            creado_por=usuario_owner,
            guia_despacho=guia,
            pedido_item=pedido_item,
            producto=producto,
            descripcion=producto.nombre,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19"),
        )
        GuiaDespachoService.recalcular_totales(guia=guia)

        guia = GuiaDespachoService.confirmar_guia(
            guia_id=guia.id,
            empresa=empresa,
            usuario=usuario_owner,
            bodega_id=None,
        )

        assert guia.estado_tributario == EstadoIntegracionTributaria.EN_COLA
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_id=guia.id,
            event_type="tributario.guia_despacho.solicitado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="sii.dte",
            event_name="guia_despacho.solicitar_emision",
        ).exists()
