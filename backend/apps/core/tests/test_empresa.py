# apps/core/tests/test_empresa.py
import pytest
from apps.core.models import Empresa, ModelPrueba
from apps.core.tenant import set_current_empresa, get_current_empresa

# Fixture para crear una empresa y dejarla activa
@pytest.fixture
def empresa_activa(db):
    empresa = Empresa.objects.create(nombre="Empresa Test", rut="11111111-1", email="test@test.com")
    set_current_empresa(empresa)
    return empresa

# Fixture para limpiar la empresa después de cada test
@pytest.fixture(autouse=True)
def limpiar_empresa():
    yield
    set_current_empresa(None)

@pytest.mark.django_db
def test_guardado_auto_empresa(empresa_activa):
    """Verifica que al guardar un objeto se asigna automáticamente la empresa del tenant"""
    obj = ModelPrueba.objects.create(nombre="Objeto A")
    assert obj.empresa == empresa_activa

@pytest.mark.django_db
def test_aislamiento_por_empresa(db):
    """Verifica que los objetos se relacionan con la empresa correcta."""
    empresa1 = Empresa.objects.create(nombre="Empresa 1", rut="11111111-1", email="a@a.com")
    empresa2 = Empresa.objects.create(nombre="Empresa 2", rut="22222222-2", email="b@b.com")

    # Crea objeto para empresa2
    set_current_empresa(empresa2)
    obj2 = ModelPrueba.objects.create(nombre="Objeto 2")

    # Crea objeto para empresa1
    set_current_empresa(empresa1)
    obj1 = ModelPrueba.objects.create(nombre="Objeto 1")

    assert obj1.empresa == empresa1
    assert obj2.empresa == empresa2

@pytest.mark.django_db
def test_all_objects_manager(db):
    """Verifica que el manager devuelva solo objetos de la empresa activa"""
    empresa1 = Empresa.objects.create(nombre="Empresa 1", rut="11111111-1", email="a@a.com")
    empresa2 = Empresa.objects.create(nombre="Empresa 2", rut="22222222-2", email="b@b.com")

    # Crea objetos para cada empresa
    set_current_empresa(empresa1)
    obj1 = ModelPrueba.objects.create(nombre="Objeto A")

    set_current_empresa(empresa2)
    obj2 = ModelPrueba.objects.create(nombre="Objeto B")

    # Activa empresa1 y consulta
    set_current_empresa(empresa1)
    objs_empresa1 = ModelPrueba.objects.all()
    assert obj1 in objs_empresa1
    assert obj2 not in objs_empresa1