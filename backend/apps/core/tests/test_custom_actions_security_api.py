from decimal import Decimal
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.core.roles import RolUsuario
from apps.contactos.models import Cliente, Contacto
from apps.presupuestos.models import Presupuesto
from apps.productos.models import Producto


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def usuario_contador_a(db, empresa_a):
    User = get_user_model()
    user = User.objects.create_user(
        username="contador_a_custom_actions",
        email="contador_a_custom_actions@test.com",
        password="pass1234",
        empresa_activa=empresa_a,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa_a, rol=RolUsuario.CONTADOR, activo=True)
    return user


@pytest.fixture
def usuario_admin_a(db, empresa_a):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_a_custom_actions",
        email="admin_a_custom_actions@test.com",
        password="pass1234",
        empresa_activa=empresa_a,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa_a, rol=RolUsuario.ADMIN, activo=True)
    return user


@pytest.fixture
def producto_empresa_b(db, empresa_b, usuario):
    # Reasignamos empresa activa para garantizar creador valido en empresa_b.
    usuario.empresa_activa = empresa_b
    usuario.save(update_fields=["empresa_activa"])

    return Producto.objects.create(
        empresa=empresa_b,
        creado_por=usuario,
        nombre="Producto B Tenancy",
        sku="TEN-B-001",
        precio_referencia=Decimal("10000"),
    )


@pytest.fixture
def presupuesto_empresa_b(db, empresa_b, usuario):
    usuario.empresa_activa = empresa_b
    usuario.save(update_fields=["empresa_activa"])

    contacto = Contacto.objects.create(
        empresa=empresa_b,
        creado_por=usuario,
        nombre="Cliente B Presupuesto",
        rut="12.345.678-5",
        email="cliente_b_presupuesto@test.com",
        tipo="EMPRESA",
    )
    cliente = Cliente.objects.create(
        empresa=empresa_b,
        creado_por=usuario,
        contacto=contacto,
    )

    return Presupuesto.objects.create(
        empresa=empresa_b,
        creado_por=usuario,
        cliente=cliente,
        numero=1,
        fecha=date.today(),
    )


@pytest.mark.django_db
class TestCustomActionsSecurityApi:
    def test_custom_action_precio_rechaza_usuario_sin_permiso(self, api_client, usuario_contador_a, empresa_a):
        producto = Producto.objects.create(
            empresa=empresa_a,
            creado_por=usuario_contador_a,
            nombre="Producto Sin Permiso",
            sku="NOPERM-001",
            precio_referencia=Decimal("5000"),
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(usuario_contador_a)}")

        response = api_client.get(reverse("producto-precio", args=[producto.id]))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permisos" in str(response.data.get("detail", "")).lower()

    def test_custom_action_precio_respeta_tenant_isolation(self, api_client, usuario_admin_a, producto_empresa_b):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(usuario_admin_a)}")

        response = api_client.get(reverse("producto-precio", args=[producto_empresa_b.id]))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_custom_action_bulk_template_proveedor_rechaza_usuario_sin_permiso(self, api_client, usuario_contador_a):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(usuario_contador_a)}")

        response = api_client.get(reverse("proveedor-bulk-template"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permiso" in str(response.data.get("detail", "")).lower()

    def test_custom_action_catalogo_estados_presupuesto_rechaza_usuario_sin_permiso(self, api_client, usuario_contador_a):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(usuario_contador_a)}")

        response = api_client.get(reverse("presupuesto-catalogo-estados"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permiso" in str(response.data.get("detail", "")).lower()

    def test_custom_action_aprobar_presupuesto_respeta_tenant_isolation(self, api_client, usuario_admin_a, presupuesto_empresa_b):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(usuario_admin_a)}")

        response = api_client.post(reverse("presupuesto-aprobar", args=[presupuesto_empresa_b.id]), {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
