import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.core.models import Empresa
from apps.productos.models import Producto, Categoria, TipoProducto
from apps.core.tenant import set_current_empresa

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(nombre="Empresa Test", rut="123-4")

@pytest.fixture
def categoria(db, empresa):
    set_current_empresa(empresa)
    return Categoria.objects.create(nombre="General")

@pytest.mark.django_db
class TestProducto:

    def test_creacion_producto_valido(self, empresa, categoria):
        """Valida que un producto estándar se cree correctamente"""
        set_current_empresa(empresa)
        prod = Producto.objects.create(
            nombre="Martillo",
            sku=" m-001 ", # Probaremos el normalize_sku del save
            precio_referencia=Decimal("1500.50"),
            categoria=categoria
        )
        assert prod.sku == "M-001"
        assert prod.maneja_inventario is True

    def test_regla_negocio_servicio(self, empresa):
        """Un servicio no debe manejar inventario ni tener stock aunque se le asigne"""
        set_current_empresa(empresa)
        servicio = Producto.objects.create(
            nombre="Instalación",
            sku="SERV-01",
            tipo=TipoProducto.SERVICIO,
            stock_actual=100, # Esto debería resetearse en el save()
            precio_referencia=Decimal("5000")
        )
        assert servicio.maneja_inventario is False
        assert servicio.stock_actual == 0

    def test_precios_no_negativos(self, empresa):
        """Valida que el orquestador use los validators de precios"""
        set_current_empresa(empresa)
        prod = Producto(
            nombre="Error",
            sku="ERR",
            precio_costo=Decimal("-100"),
            precio_referencia=Decimal("100")
        )
        with pytest.raises(ValidationError) as excinfo:
            prod.full_clean()
        assert "precio costo" in str(excinfo.value)

    def test_unicidad_sku_por_empresa(self, empresa):
        """Verifica que el unique_together funcione con el full_clean"""
        set_current_empresa(empresa)
        Producto.objects.create(nombre="P1", sku="SKU-X", precio_referencia=10)
        
        with pytest.raises(ValidationError):
            # El segundo debe fallar por el SKU duplicado
            Producto.objects.create(nombre="P2", sku="SKU-X", precio_referencia=20)

    def test_stock_negativo_prohibido(self, empresa):
        """Valida que el stock no pueda ser menor a cero si maneja inventario"""
        set_current_empresa(empresa)
        prod = Producto(
            nombre="Producto Fallido",
            sku="FAIL",
            stock_actual=Decimal("-5"),
            maneja_inventario=True,
            precio_referencia=10
        )
        with pytest.raises(ValidationError) as excinfo:
            prod.full_clean()
        assert "stock no puede ser negativo" in str(excinfo.value)