import pytest
from django.core.exceptions import ValidationError
from apps.core.models import Empresa
from apps.productos.models import Categoria, Producto
from apps.core.tenant import set_current_empresa

@pytest.fixture
def empresa_a(db):
    return Empresa.objects.create(nombre="Empresa A", rut="1-1")

@pytest.fixture
def empresa_b(db):
    return Empresa.objects.create(nombre="Empresa B", rut="2-2")

@pytest.mark.django_db
class TestCategoria:

    def test_normalizacion_nombre(self, empresa_a):
        """Verifica que '  electrónica  ' se guarde como 'ELECTRÓNICA'"""
        set_current_empresa(empresa_a)
        cat = Categoria.objects.create(nombre="  electrónica  ")
        assert cat.nombre == "ELECTRÓNICA"

    def test_unicidad_por_empresa(self, empresa_a, empresa_b):
        """Dos empresas pueden tener la misma categoría, pero una no puede repetirla"""
        set_current_empresa(empresa_a)
        Categoria.objects.create(nombre="Ferretería")
        
        # 1. Intentar duplicar en Empresa A (Debe fallar)
        with pytest.raises(ValidationError):
            Categoria.objects.create(nombre="ferretería") # El capitalize() lo haría igual

        # 2. Crear en Empresa B (Debe permitirlo)
        set_current_empresa(empresa_b)
        cat_b = Categoria.objects.create(nombre="Ferretería")
        assert cat_b.pk is not None

    def test_seguridad_cross_tenant_producto(self, empresa_a, empresa_b):
        """
        PRUEBA DE FUEGO: Un producto de Empresa B no puede usar 
        una categoría de Empresa A.
        """
        # 1. Empresa A crea una categoría
        set_current_empresa(empresa_a)
        cat_a = Categoria.objects.create(nombre="Categoría Privada A")

        # 2. Empresa B intenta crear un producto usando la categoría de A
        set_current_empresa(empresa_b)
        producto_b = Producto(
            nombre="Producto Espía",
            sku="ESP-001",
            categoria=cat_a, # <-- Aquí está la intrusión
            empresa=empresa_b
        )

        # 3. Debe fallar al validar
        with pytest.raises(ValidationError) as excinfo:
            producto_b.full_clean()
        
        assert "categoria" in excinfo.value.message_dict
        assert "no pertenece a su empresa" in str(excinfo.value)

    def test_proteccion_borrado_con_productos(self, empresa_a):
        """No se puede borrar una categoría si tiene productos asociados"""
        from django.db.models.deletion import ProtectedError
        
        set_current_empresa(empresa_a)
        cat = Categoria.objects.create(nombre="Construcción")
        Producto.objects.create(nombre="Cemento", sku="CEM-01", categoria=cat)

        with pytest.raises(ProtectedError):
            cat.delete()