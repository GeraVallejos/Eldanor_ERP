import pytest
from django.test import RequestFactory
from apps.core.middleware import EmpresaMiddleware
from apps.core.tenant import get_current_empresa, set_current_empresa, set_current_user
from apps.core.models import Empresa, ModelPrueba

# --- FIXTURES ---

@pytest.fixture
def empresa_activa(db):
    empresa = Empresa.objects.create(nombre="Empresa Test", rut="11111111-1", email="test@test.com")
    set_current_empresa(empresa)
    yield empresa
    set_current_empresa(None)

@pytest.fixture
def user_con_empresa(db, empresa_activa):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username="testuser", 
        email="test@test.com", 
        password="pass", 
        empresa=empresa_activa
    )

# --- TESTS ---

@pytest.mark.django_db
def test_middleware_setea_empresa_correctamente(user_con_empresa):
    """Verifica que el middleware asigne la empresa al contexto"""
    factory = RequestFactory()
    request = factory.get('/')
    request.user = user_con_empresa

    # Para probar que funcionó, capturamos el valor DENTRO de la respuesta
    # ya que el middleware limpia el contexto al salir.
    contexto = {}
    def get_response(req):
        contexto['empresa'] = get_current_empresa()
        return None

    middleware = EmpresaMiddleware(get_response)
    middleware(request)

    assert contexto['empresa'] == user_con_empresa.empresa

@pytest.mark.django_db
def test_prohibir_cambio_de_empresa(empresa_activa):
    """Verifica seguridad del BaseModel"""
    obj = ModelPrueba.objects.create(nombre="Original")
    empresa_b = Empresa.objects.create(nombre="Empresa B", rut="222-2", email="b@b.com")
    
    obj.empresa = empresa_b
    with pytest.raises(ValueError, match="La empresa propietaria no puede ser modificada"):
        obj.save()

@pytest.mark.django_db
def test_asignacion_automatica_usuario(empresa_activa, user_con_empresa):
    """Verifica asignación de creado_por"""
    set_current_user(user_con_empresa)
    obj = ModelPrueba.objects.create(nombre="Test Usuario")
    assert obj.creado_por == user_con_empresa
    set_current_user(None)

@pytest.mark.django_db
def test_diferencia_entre_managers(db):
    from apps.core.models import Empresa, ModelPrueba
    from apps.core.tenant import set_current_empresa
    
    emp1 = Empresa.objects.create(nombre="E1", rut="1-1")
    emp2 = Empresa.objects.create(nombre="E2", rut="2-2")
    
    # Crear uno en cada una
    set_current_empresa(emp1)
    ModelPrueba.objects.create(nombre="Obj1")
    
    set_current_empresa(emp2)
    ModelPrueba.objects.create(nombre="Obj2")
    
    # Test Manager filtrado
    set_current_empresa(emp1)
    assert ModelPrueba.objects.count() == 1
    
    # Test Manager total (all_objects)
    assert ModelPrueba.all_objects.count() == 2

