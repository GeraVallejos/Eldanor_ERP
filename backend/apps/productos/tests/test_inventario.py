import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from apps.core.models import Empresa, User
from apps.productos.models import Producto, TipoProducto
from apps.productos.models.movimiento import TipoMovimiento, MovimientoInventario
from apps.productos.services.inventario_service import InventarioService
from apps.core.tenant import set_current_empresa

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(nombre="Empresa Logística S.A.", rut="99.888.777-6")

@pytest.fixture
def usuario(db):
    # Creamos un usuario para el campo 'creado_por' que hereda del BaseModel
    return User.objects.create(username="admin_bodega")

@pytest.fixture
def producto_fisico(db, empresa):
    set_current_empresa(empresa)
    return Producto.objects.create(
        nombre="Taladro Percutor",
        sku="TAL-01",
        stock_actual=Decimal("0.00"),
        maneja_inventario=True,
        precio_referencia=Decimal("50000")
    )

@pytest.mark.django_db
class TestInventarioService:

    def test_entrada_stock_actualiza_producto_y_kardex(self, empresa, producto_fisico, usuario):
        """Verifica que una entrada sume al stock y registre los saldos anterior/nuevo"""
        set_current_empresa(empresa)
        cantidad_entrada = Decimal("10.50")
        
        mov = InventarioService.registrar_movimiento(
            producto=producto_fisico,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=cantidad_entrada,
            referencia="Compra factura #45",
            empresa=empresa,
            usuario=usuario
        )

        # Validar el registro del movimiento (Kardex)
        assert mov.stock_anterior == Decimal("0.00")
        assert mov.stock_nuevo == Decimal("10.50")
        assert mov.tipo == TipoMovimiento.ENTRADA

        # Validar la actualización en el producto
        producto_fisico.refresh_from_db()
        assert producto_fisico.stock_actual == Decimal("10.50")

    def test_salida_stock_descuenta_correctamente(self, empresa, producto_fisico, usuario):
        """Verifica que una salida reste stock basándose en el saldo actual"""
        set_current_empresa(empresa)
        # Seteamos un stock inicial de 100
        producto_fisico.stock_actual = Decimal("100.00")
        producto_fisico.save()

        InventarioService.registrar_movimiento(
            producto=producto_fisico,
            tipo=TipoMovimiento.SALIDA,
            cantidad=Decimal("30.00"),
            referencia="Venta nota de pedido #1",
            empresa=empresa,
            usuario=usuario
        )

        producto_fisico.refresh_from_db()
        assert producto_fisico.stock_actual == Decimal("70.00")

    def test_error_cuando_stock_es_insuficiente(self, empresa, producto_fisico, usuario):
        """No debe permitir salidas que dejen el stock en negativo"""
        set_current_empresa(empresa)
        producto_fisico.stock_actual = Decimal("5.00")
        producto_fisico.save()

        with pytest.raises(ValidationError) as excinfo:
            InventarioService.registrar_movimiento(
                producto=producto_fisico,
                tipo=TipoMovimiento.SALIDA,
                cantidad=Decimal("10.00"),
                referencia="Intento de venta sin stock",
                empresa=empresa,
                usuario=usuario
            )
        
        assert "Stock insuficiente" in str(excinfo.value)

    def test_bloqueo_movimiento_en_servicios(self, empresa, usuario):
        """Un servicio no puede tener movimientos de inventario"""
        set_current_empresa(empresa)
        servicio = Producto.objects.create(
            nombre="Asesoría Técnica",
            sku="SERV-001",
            tipo=TipoProducto.SERVICIO,
            maneja_inventario=False,
            precio_referencia=Decimal("1000")
        )

        with pytest.raises(ValidationError) as excinfo:
            InventarioService.registrar_movimiento(
                producto=servicio,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=Decimal("1.00"),
                referencia="Error",
                empresa=empresa,
                usuario=usuario
            )
        
        assert "no maneja inventario" in str(excinfo.value)