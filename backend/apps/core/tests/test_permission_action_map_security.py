from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.core.models import Empresa, UserEmpresa
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion
from apps.core.roles import RolUsuario


@pytest.mark.django_db
class TestPermissionActionMapSecurity:
    def test_deniega_accion_no_mapeada_en_permission_action_map(self):
        User = get_user_model()
        empresa = Empresa.objects.create(
            nombre="Empresa Permisos",
            rut="11111111-1",
            email="empresa_permisos@test.com",
        )
        user = User.objects.create_user(
            username="contador_permiso",
            email="contador_permiso@test.com",
            password="pass1234",
            empresa_activa=empresa,
        )
        UserEmpresa.objects.create(user=user, empresa=empresa, rol=RolUsuario.CONTADOR, activo=True)

        request = APIRequestFactory().get("/api/productos/productos/1/precio/")
        request.user = user

        view = SimpleNamespace(
            permission_modulo=Modulos.PRODUCTOS,
            permission_action_map={
                "list": Acciones.VER,
                "retrieve": Acciones.VER,
            },
            action="precio",
        )

        permission = TienePermisoModuloAccion()
        assert permission.has_permission(request, view) is False
        assert permission.message == "La accion no esta mapeada en permission_action_map."
