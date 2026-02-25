import pytest
from django.core.exceptions import ValidationError
from apps.core.models import Empresa
from apps.contactos.models import Contacto, Cliente, Proveedor, Direccion, CuentaBancaria
from apps.core.tenant import set_current_empresa

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(nombre="Constructora Maipo", rut="77.888.999-0")

@pytest.mark.django_db
class TestModuloContactos:

    def test_creacion_contacto_normaliza_rut(self, empresa):
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Juan Perez",
            rut="18123123k"
        )
        assert contacto.rut == "18.123.123-K"

    def test_un_contacto_puede_ser_cliente_y_proveedor(self, empresa):
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(empresa=empresa, nombre="Sodimac", rut="99.555.444-3")
        
        Cliente.objects.create(contacto=contacto, limite_credito=1000000)
        Proveedor.objects.create(contacto=contacto, giro="Venta materiales")

        assert hasattr(contacto, 'cliente')
        assert hasattr(contacto, 'proveedor')

    def test_unicidad_rut_por_empresa(self, empresa):
        """Captura ValidationError porque Django detecta el duplicado antes de ir a DB"""
        set_current_empresa(empresa)
        rut_test = "11.111.111-1"
        Contacto.objects.create(empresa=empresa, nombre="Empresa A", rut=rut_test)

        # Cambiamos IntegrityError por ValidationError
        with pytest.raises(ValidationError):
            # Usamos una instancia nueva y llamamos a full_clean() o dejamos que el save valide
            nuevo = Contacto(empresa=empresa, nombre="Empresa B", rut=rut_test)
            nuevo.full_clean() 

    def test_direccion_unica_por_tipo(self, empresa):
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(empresa=empresa, nombre="Test", rut="11.111.111-K")
        Direccion.objects.create(contacto=contacto, tipo="despacho", direccion="Calle 1", comuna="Stgo", ciudad="Stgo")
        
        # Aquí sí suele saltar IntegrityError porque es un Constraint de Meta
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Direccion.objects.create(contacto=contacto, tipo="despacho", direccion="Calle 2", comuna="Stgo", ciudad="Stgo")

    def test_rut_titular_cuenta_bancaria_normaliza(self, empresa):
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(empresa=empresa, nombre="Titular Test", rut="22.222.222-2")
        
        cuenta = CuentaBancaria.objects.create(
            contacto=contacto,
            banco="Banco Estado",
            tipo_cuenta="corriente",
            numero_cuenta="123456",
            titular="Pedro",
            rut_titular="15555444k" 
        )
        
        # Recargamos de la DB para asegurar que el save() hizo su magia
        cuenta.refresh_from_db()
        assert cuenta.rut_titular == "15.555.444-K"