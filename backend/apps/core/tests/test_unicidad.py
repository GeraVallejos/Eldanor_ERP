import pytest
from django.test import RequestFactory
from apps.core.tenant import set_current_empresa
from apps.core.models import Empresa
from django.core.exceptions import ValidationError

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
def test_context_leak_entre_peticiones(user_con_empresa, db):
    """
    Verifica que el contexto se limpie después de una petición 
    y no afecte a la siguiente.
    """
    from apps.core.middleware import EmpresaMiddleware
    from apps.core.tenant import get_current_empresa
    factory = RequestFactory()

    # 1. Simular Petición A (Usuario Autenticado)
    request_a = factory.get('/')
    request_a.user = user_con_empresa
    middleware = EmpresaMiddleware(lambda r: None)
    middleware(request_a)
    
    # Al salir del middleware, el contexto DEBE ser None (por el set(None) que pusimos)
    assert get_current_empresa() is None

    # 2. Simular Petición B (Usuario Anónimo o sin empresa)
    request_b = factory.get('/')
    from django.contrib.auth.models import AnonymousUser
    request_b.user = AnonymousUser()
    
    middleware(request_b)
    
    # Verificamos que no heredó la empresa de la petición anterior
    assert get_current_empresa() is None


@pytest.mark.django_db
def test_unicidad_cruzada_rut_cliente(db):
    """
    Verifica que dos empresas puedan tener un cliente con el mismo RUT,
    pero una misma empresa no pueda duplicarlo.
    """
    from apps.core.models import Empresa, Cliente
    from apps.core.tenant import set_current_empresa
    from django.db import IntegrityError

    # 1. Crear Empresa A y su Cliente
    emp_a = Empresa.objects.create(nombre="Empresa A", rut="1-1", email="a@test.com")
    set_current_empresa(emp_a)
    Cliente.objects.create(nombre="Cliente A", rut="12345-K", empresa=emp_a)

    # 2. Crear Empresa B e intentar usar el MISMO RUT (Debe permitirlo)
    emp_b = Empresa.objects.create(nombre="Empresa B", rut="2-2", email="b@test.com")
    set_current_empresa(emp_b)
    cliente_b = Cliente.objects.create(nombre="Cliente B", rut="12345-K", empresa=emp_b)
    
    assert cliente_b.pk is not None # Se guardó correctamente

    # 3. Intentar duplicar RUT en la MISMA Empresa B (Debe fallar)
    with pytest.raises(ValidationError):
        Cliente.objects.create(nombre="Cliente B Duplicado", rut="12345-K", empresa=emp_b)


@pytest.mark.django_db
def test_intrusión_de_datos_bloqueada(db):
    """
    Verifica que no se pueda acceder a un objeto de otra empresa
    incluso conociendo su ID (UUID).
    """
    from apps.core.models import Empresa, ModelPrueba
    from apps.core.tenant import set_current_empresa
    from django.core.exceptions import ObjectDoesNotExist
    
    # 1. Empresa A crea un registro secreto
    emp_a = Empresa.objects.create(nombre="Empresa A", rut="1-1")
    set_current_empresa(emp_a)
    obj_a = ModelPrueba.objects.create(nombre="Secreto de A")
    id_secreto = obj_a.id
    
    # 2. Cambiamos a Empresa B
    emp_b = Empresa.objects.create(nombre="Empresa B", rut="2-2")
    set_current_empresa(emp_b)
    
    # 3. Empresa B intenta 'adivinar' o acceder al ID de la Empresa A
    with pytest.raises(ObjectDoesNotExist):
        ModelPrueba.objects.get(id=id_secreto)