import pytest
from django.test import RequestFactory
from apps.core.tenant import set_current_empresa
from apps.core.models import Empresa
from apps.contactos.models import Contacto, Cliente
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
def test_unicidad_cruzada_rut_cliente():
    """
    Verifica que el RUT sea único por empresa a nivel de Contacto,
    lo que protege indirectamente a los Clientes.
    """
    
    # 1. Crear Empresa A y su Contacto/Cliente
    emp_a = Empresa.objects.create(nombre="EMPRESA A", rut="11.111.111-1")
    set_current_empresa(emp_a)
    
    contacto_a = Contacto.objects.create(
        nombre="CLIENTE A", 
        rut="12.345.678-K", 
        empresa=emp_a
    )
    Cliente.objects.create(contacto=contacto_a)

    # 2. Crear Empresa B e intentar usar el MISMO RUT (Debe permitirlo en otra empresa)
    emp_b = Empresa.objects.create(nombre="EMPRESA B", rut="22.222.222-2")
    set_current_empresa(emp_b)
    
    contacto_b = Contacto.objects.create(
        nombre="CLIENTE B", 
        rut="12.345.678-K", 
        empresa=emp_b
    )
    cliente_b = Cliente.objects.create(contacto=contacto_b)
    
    assert cliente_b.pk is not None  # Se guardó correctamente en empresa B

    # 3. Intentar duplicar RUT en la MISMA Empresa B (Debe fallar en el Contacto)
    with pytest.raises(ValidationError):
        # El clean() del modelo Contacto detectará el duplicado antes de llegar a Cliente
        nuevo_contacto = Contacto(
            nombre="CLIENTE B DUPLICADO", 
            rut="12.345.678-K", 
            empresa=emp_b
        )
        nuevo_contacto.full_clean() # Gatilla la validación de unicidad


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