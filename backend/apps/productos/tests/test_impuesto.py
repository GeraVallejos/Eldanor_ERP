import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.core.models import Empresa
from apps.productos.models import Impuesto
from apps.core.tenant import set_current_empresa

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(nombre="Empresa Tax Test", rut="555-5")

@pytest.mark.django_db
class TestImpuesto:

    def test_creacion_impuesto_valido(self, empresa):
        """Verifica que un impuesto estándar (como el IVA) se cree bien"""
        set_current_empresa(empresa)
        iva = Impuesto.objects.create(
            nombre="IVA",
            porcentaje=Decimal("19.00")
        )
        assert iva.nombre == "IVA" # Por el capitalize() que pusimos en el save
        assert iva.porcentaje == Decimal("19.00")

    def test_impuesto_no_negativo(self, empresa):
        """El porcentaje no puede ser menor a 0"""
        set_current_empresa(empresa)
        imp = Impuesto(nombre="Error", porcentaje=Decimal("-5"))
        with pytest.raises(ValidationError):
            imp.full_clean()

    def test_impuesto_maximo(self, empresa):
        """El porcentaje no puede ser mayor a 100 (regla de negocio)"""
        set_current_empresa(empresa)
        imp = Impuesto(nombre="Usura", porcentaje=Decimal("101"))
        with pytest.raises(ValidationError):
            imp.full_clean()

    def test_unicidad_impuesto_por_empresa(self, empresa):
        """No se pueden repetir nombres de impuestos en la misma empresa (Case Insensitive por normalización)"""
        set_current_empresa(empresa)
        
        # 1. Creamos el primer impuesto
        Impuesto.objects.create(nombre="IVA", porcentaje=19)
        
        # 2. Intentamos crear un duplicado. 
        # Usamos full_clean() porque es donde vive la lógica de validación de Django
        with pytest.raises(ValidationError):
            impuesto_duplicado = Impuesto(nombre="iva", porcentaje=10) # En minúsculas para probar normalización
            impuesto_duplicado.full_clean() 
            impuesto_duplicado.save()

    def test_unicidad_impuesto_db_level(self, empresa):
        """Prueba que el sistema no permita nombres duplicados"""
        set_current_empresa(empresa)
        Impuesto.objects.create(nombre="RETENCION", porcentaje=10)
        
        # Como Django detecta el UniqueConstraint en el momento del .create(),
        # lanza ValidationError antes de llegar a la base de datos.
        with pytest.raises(ValidationError):
            Impuesto.objects.create(nombre="RETENCION", porcentaje=15)