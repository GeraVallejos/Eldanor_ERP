import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.core.permisos.constantes_permisos import Modulos, Acciones



def obtener_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="owner_perm",
        email="owner_perm@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )

    UserEmpresa.objects.create(
        user=user,
        empresa=empresa,
        rol="OWNER",
        activo=True,
    )
    return user


@pytest.fixture
def vendedor_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="vend_perm",
        email="vend_perm@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )

    relacion = UserEmpresa.objects.create(
        user=user,
        empresa=empresa,
        rol="VENDEDOR",
        activo=True,
    )
    return user, relacion


@pytest.fixture
def admin_usuario(db, empresa):
    from django.contrib.auth import get_user_model
    from apps.core.permisos.permisoModulo import PermisoModulo
    from apps.core.permisos.services import sincronizar_catalogo_permisos

    User = get_user_model()
    user = User.objects.create_user(
        username="admin_perm",
        email="admin_perm@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )

    relacion = UserEmpresa.objects.create(
        user=user,
        empresa=empresa,
        rol="ADMIN",
        activo=True,
    )

    sincronizar_catalogo_permisos()
    relacion.permisos.add(PermisoModulo.objects.get(codigo="TESORERIA.VER"))
    return user, relacion


@pytest.mark.django_db
class TestGestionPermisosAPI:
    def test_owner_puede_ver_catalogo(self, api_client, owner_usuario):
        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get(reverse("permisos-catalogo"))

        assert response.status_code == status.HTTP_200_OK
        assert "PRESUPUESTOS" in response.data
        assert Acciones.GESTIONAR_PERMISOS in response.data[Modulos.ADMINISTRACION]

    def test_owner_puede_asignar_permiso_personalizado(self, api_client, owner_usuario, vendedor_usuario):
        _, relacion_vendedor = vendedor_usuario

        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = {
            "relacion_id": str(relacion_vendedor.id),
            "permisos": ["PRESUPUESTOS.APROBAR"],
        }

        response = api_client.post(reverse("permisos-asignar"), payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        relacion_vendedor.refresh_from_db()
        assert relacion_vendedor.permisos.filter(codigo="PRESUPUESTOS.APROBAR").exists()
        assert "PRESUPUESTOS.APROBAR" in response.data["permisos_efectivos"]

    def test_vendedor_no_puede_gestionar_permisos(self, api_client, vendedor_usuario):
        vendedor, relacion_vendedor = vendedor_usuario

        token = obtener_token(vendedor)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = {
            "relacion_id": str(relacion_vendedor.id),
            "permisos": ["PRESUPUESTOS.APROBAR"],
        }

        response = api_client.post(reverse("permisos-asignar"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error_code"] == "PERMISSION_DENIED"

    def test_owner_recibe_error_normalizado_si_envia_permisos_invalidos(self, api_client, owner_usuario, vendedor_usuario):
        _, relacion_vendedor = vendedor_usuario

        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.post(
            reverse("permisos-asignar"),
            {
                "relacion_id": str(relacion_vendedor.id),
                "permisos": ["ERP.NO_EXISTE"],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_code"] == "VALIDATION_ERROR"
        assert response.data["meta"]["invalidos"] == ["ERP.NO_EXISTE"]

    def test_permiso_personalizado_cambia_permisos_efectivos(self, owner_usuario, vendedor_usuario):
        vendedor, relacion_vendedor = vendedor_usuario

        assert not vendedor.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, owner_usuario.empresa_activa)

        from apps.core.permisos.services import sincronizar_catalogo_permisos
        from apps.core.permisos.permisoModulo import PermisoModulo

        sincronizar_catalogo_permisos()
        permiso = PermisoModulo.objects.get(codigo="PRESUPUESTOS.APROBAR")
        relacion_vendedor.permisos.add(permiso)

        assert vendedor.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, owner_usuario.empresa_activa)

    def test_owner_puede_listar_miembros_y_permisos(self, api_client, owner_usuario, vendedor_usuario):
        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get(reverse("permisos-miembros-empresa"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
        assert any(item["rol"] == "OWNER" for item in response.data)
        assert any(item["rol"] == "VENDEDOR" for item in response.data)

    def test_admin_mantiene_permisos_totales_aunque_tenga_personalizados(self, admin_usuario):
        admin, relacion = admin_usuario

        from apps.core.permisos.services import permisos_efectivos_relacion

        efectivos = permisos_efectivos_relacion(relacion)

        assert efectivos == ["*"]
        assert admin.tiene_permiso(Modulos.COMPRAS, Acciones.APROBAR, admin.empresa_activa) is True
