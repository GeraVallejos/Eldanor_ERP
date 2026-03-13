import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.auditoria.services import AuditoriaService
from apps.core.models import UserEmpresa
from apps.core.roles import RolUsuario


@pytest.mark.django_db
class TestAuditoriaApi:
    def test_lista_eventos_filtrados_por_modulo(self, api_client, empresa, usuario):
        UserEmpresa.objects.create(user=usuario, empresa=empresa, rol=RolUsuario.ADMIN, activo=True)
        api_client.force_authenticate(user=usuario)

        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="PRESUPUESTOS",
            action_code="APROBAR",
            event_type="PRESUPUESTO_APROBADO",
            entity_type="PRESUPUESTO",
            entity_id="1",
            summary="Presupuesto aprobado",
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="EDITAR",
            event_type="CLIENTE_ACTUALIZADO",
            entity_type="CLIENTE",
            entity_id="1",
            summary="Cliente actualizado",
        )

        response = api_client.get("/api/auditoria/eventos/?module_code=PRESUPUESTOS")

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["module_code"] == "PRESUPUESTOS"

    def test_integridad_cadena_retorna_ok(self, api_client, empresa, usuario):
        UserEmpresa.objects.create(user=usuario, empresa=empresa, rol=RolUsuario.ADMIN, activo=True)
        api_client.force_authenticate(user=usuario)

        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="INVENTARIO",
            action_code="EDITAR",
            event_type="INVENTARIO_MOVIMIENTO_REGISTRADO",
            entity_type="MOVIMIENTO_INVENTARIO",
            entity_id="mv-1",
            summary="Movimiento registrado",
        )

        response = api_client.get("/api/auditoria/eventos/integridad/")

        assert response.status_code == 200
        assert response.data["is_valid"] is True
        assert response.data["total_events"] == 1

    def test_bloquea_usuario_sin_permiso_modulo(self, api_client, empresa):
        User = get_user_model()
        email_token = uuid.uuid4().hex[:8]
        vendedor = User.objects.create_user(
            username=f"vendedor_{email_token}",
            email=f"vendedor_{email_token}@test.com",
            password="pass1234",
            empresa_activa=empresa,
        )
        UserEmpresa.objects.create(user=vendedor, empresa=empresa, rol=RolUsuario.VENDEDOR, activo=True)

        api_client.force_authenticate(user=vendedor)

        response = api_client.get("/api/auditoria/eventos/")

        assert response.status_code == 403
