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
        """Prueba que el clean y save de Contacto formatean el RUT correctamente"""
        set_current_empresa(empresa)
        # Ingresamos un RUT sucio
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Juan Perez",
            rut="18123123k"
        )
        # Debe guardarse con puntos, guion y K mayúscula
        assert contacto.rut == "18.123.123-K"

    def test_un_contacto_puede_ser_cliente_y_proveedor(self, empresa):
        """Prueba la arquitectura de delegación: un contacto, dos roles"""
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(empresa=empresa, nombre="Sodimac", rut="99.555.444-3")
        
        # Creamos los roles apuntando al mismo contacto
        cliente = Cliente.objects.create(contacto=contacto, limite_credito=1000000)
        proveedor = Proveedor.objects.create(contacto=contacto, giro="Venta materiales")

        assert contacto.cliente is not None
        assert contacto.proveedor is not None
        assert contacto.cliente.limite_credito == 1000000

    def test_unicidad_rut_por_empresa(self, empresa):
        """Prueba que el UniqueConstraint funcione correctamente"""
        set_current_empresa(empresa)
        rut_test = "11.111.111-1"
        Contacto.objects.create(empresa=empresa, nombre="Empresa A", rut=rut_test)

        with pytest.raises(Exception): # Captura error de integridad de la DB
            Contacto.objects.create(empresa=empresa, nombre="Empresa B", rut=rut_test)

    def test_direccion_unica_por_tipo(self, empresa):
        """Prueba que no se puedan tener dos direcciones de 'despacho' para el mismo contacto"""
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(empresa=empresa, nombre="Test", rut="1-9")
        
        Direccion.objects.create(contacto=contacto, tipo="despacho", direccion="Calle 1", comuna="Stgo", ciudad="Stgo")
        
        with pytest.raises(Exception):
            Direccion.objects.create(contacto=contacto, tipo="despacho", direccion="Calle 2", comuna="Stgo", ciudad="Stgo")

    def test_rut_titular_cuenta_bancaria_normaliza(self, empresa):
        """Prueba que el RUT del titular en la cuenta bancaria también se formatee"""
        set_current_empresa(empresa)
        contacto = Contacto.objects.create(empresa=empresa, nombre="Titular Test", rut="2-7")
        
        cuenta = CuentaBancaria.objects.create(
            contacto=contacto,
            banco="Banco Estado",
            tipo_cuenta="corriente",
            numero_cuenta="123456",
            titular="Pedro",
            rut_titular="15555444k" # Sucio
        )
        
        # Si agregaste el save() en CuentaBancaria como sugerí:
        assert cuenta.rut_titular == "15.555.444-K"