import pytest
from rest_framework import status
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.models import UserEmpresa
from apps.contactos.models import Contacto, Cliente
from apps.presupuestos.models import Presupuesto, EstadoPresupuesto
from datetime import date


# =========================================================
# FIXTURES BASE
# =========================================================

@pytest.fixture
def relacion_activa(usuario, empresa):
    return UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol="OWNER",
        activo=True
    )


@pytest.fixture
def relacion_inactiva(usuario, empresa):
    return UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol="OWNER",
        activo=False
    )


# =========================================================
# CLIENTE COMPLETO
# =========================================================

@pytest.fixture
def cliente_empresa_a(empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Cliente A",
        rut="33333333-3",
        email="clienteA@test.com",
        tipo="EMPRESA",
    )

    return Cliente.objects.create(
        empresa=empresa,
        contacto=contacto
    )


@pytest.fixture
def cliente_empresa_b(empresa_b):
    contacto = Contacto.objects.create(
        empresa=empresa_b,
        nombre="Cliente B",
        rut="44444444-4",
        email="clienteB@test.com",
        tipo="EMPRESA",
    )

    return Cliente.objects.create(
        empresa=empresa_b,
        contacto=contacto
    )


# =========================================================
# PRESUPUESTOS 
# =========================================================

@pytest.fixture
def presupuesto_empresa_a(empresa, cliente_empresa_a):
    return Presupuesto.objects.create(
        empresa=empresa,
        cliente=cliente_empresa_a,
        numero=1,
        fecha=date.today(),
        estado=EstadoPresupuesto.BORRADOR
    )


@pytest.fixture
def presupuesto_empresa_b(empresa_b, cliente_empresa_b):
    return Presupuesto.objects.create(
        empresa=empresa_b,
        cliente=cliente_empresa_b,
        numero=1,
        fecha=date.today(),
        estado=EstadoPresupuesto.BORRADOR
    )


# =========================================================
# UTIL
# =========================================================

def obtener_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


# =========================================================
# TESTS
# =========================================================

@pytest.mark.django_db
class TestPermisosAPI:


    def test_usuario_sin_empresa_activa_devuelve_403(
        self,
        api_client,
        usuario,
        presupuesto_empresa_a,
        relacion_activa
    ):
        usuario.empresa_activa = None
        usuario.save()

        token = obtener_token(usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("presupuesto-detail", args=[presupuesto_empresa_a.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_relacion_inactiva_devuelve_403(
        self,
        api_client,
        usuario,
        empresa,
        presupuesto_empresa_a,
        relacion_inactiva
    ):
        usuario.empresa_activa = empresa
        usuario.save()

        token = obtener_token(usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("presupuesto-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_no_puede_acceder_a_empresa_ajena_devuelve_404(
        self,
        api_client,
        usuario,
        empresa,
        presupuesto_empresa_b,
        relacion_activa
    ):
        usuario.empresa_activa = empresa
        usuario.save()

        token = obtener_token(usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("presupuesto-detail", args=[presupuesto_empresa_b.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


    def test_usuario_con_relacion_activa_accede_200(
        self,
        api_client,
        usuario,
        empresa,
        presupuesto_empresa_a,
        relacion_activa
    ):
        usuario.empresa_activa = empresa
        usuario.save()

        token = obtener_token(usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        url = reverse("presupuesto-detail", args=[presupuesto_empresa_a.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
