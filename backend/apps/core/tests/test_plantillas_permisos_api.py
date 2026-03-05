import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.core.permisos.constantes_permisos import Acciones, Modulos



def obtener_token(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="owner_tpl",
        email="owner_tpl@test.com",
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
        username="vend_tpl",
        email="vend_tpl@test.com",
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


@pytest.mark.django_db
class TestPlantillasPermisosAPI:
    def test_owner_lista_plantillas_base(self, api_client, owner_usuario):
        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get(reverse("permisos-plantillas"))

        assert response.status_code == status.HTTP_200_OK
        codigos = {item["codigo"] for item in response.data}
        assert "VENTAS_BASE" in codigos
        assert "FINANZAS_BASE" in codigos

    def test_owner_crea_y_actualiza_plantilla(self, api_client, owner_usuario):
        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        payload = {
            "codigo": "operaciones_custom",
            "nombre": "Operaciones Custom",
            "descripcion": "Plantilla editable",
            "permisos": ["COMPRAS.VER", "COMPRAS.APROBAR", "TESORERIA.VER"],
            "activa": True,
        }

        crear = api_client.post(reverse("permisos-plantillas"), payload, format="json")
        assert crear.status_code == status.HTTP_201_CREATED
        assert crear.data["codigo"] == "OPERACIONES_CUSTOM"

        actualizar = api_client.patch(
            reverse("permisos-plantillas-detalle", args=["OPERACIONES_CUSTOM"]),
            {
                "nombre": "Operaciones Plus",
                "permisos": ["COMPRAS.VER", "COMPRAS.APROBAR", "COMPRAS.EDITAR"],
            },
            format="json",
        )
        assert actualizar.status_code == status.HTTP_200_OK
        assert actualizar.data["nombre"] == "Operaciones Plus"
        assert "COMPRAS.EDITAR" in actualizar.data["permisos"]

    def test_owner_aplica_plantilla_a_usuario(self, api_client, owner_usuario, vendedor_usuario):
        vendedor, relacion = vendedor_usuario
        token = obtener_token(owner_usuario)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.post(
            reverse("permisos-plantillas-aplicar"),
            {
                "relacion_id": relacion.id,
                "plantilla_codigo": "VENTAS_BASE",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        vendedor.refresh_from_db()
        assert vendedor.tiene_permiso(Modulos.VENTAS, Acciones.CREAR, owner_usuario.empresa_activa)

    def test_vendedor_no_puede_administrar_plantillas(self, api_client, vendedor_usuario):
        vendedor, _ = vendedor_usuario
        token = obtener_token(vendedor)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get(reverse("permisos-plantillas"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
