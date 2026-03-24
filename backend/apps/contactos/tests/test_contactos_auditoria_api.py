import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.models import AuditEvent
from apps.contactos.models import Contacto
from apps.core.models import UserEmpresa


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def admin_usuario(db, empresa):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"admin_contactos_{suffix}",
        email=f"admin_contactos_{suffix}@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)
    return user


@pytest.mark.django_db
class TestContactosAuditoriaApi:
    def test_contacto_crud_registra_auditoria(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        create_response = api_client.post(
            reverse("contacto-list"),
            {
                "nombre": "Contacto Auditoria",
                "rut": "11111111-1",
                "tipo": "EMPRESA",
                "email": "contacto.auditoria@test.com",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        contacto_id = create_response.data["id"]

        update_response = api_client.patch(
            reverse("contacto-detail", args=[contacto_id]),
            {"telefono": "99999999"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK

        delete_response = api_client.delete(reverse("contacto-detail", args=[contacto_id]))
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        eventos = AuditEvent.all_objects.filter(empresa=empresa, entity_type="CONTACTO")
        event_types = set(eventos.values_list("event_type", flat=True))

        assert "CONTACTO_CREADO" in event_types
        assert "CONTACTO_ACTUALIZADO" in event_types
        assert "CONTACTO_ELIMINADO" in event_types

    def test_cliente_y_proveedor_registran_auditoria(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Contacto Base",
            rut="22222222-2",
            tipo="EMPRESA",
            email="contacto.base@test.com",
        )

        cliente_response = api_client.post(
            reverse("cliente-list"),
            {
                "contacto": str(contacto.id),
                "limite_credito": "100000",
                "dias_credito": 15,
            },
            format="json",
        )
        assert cliente_response.status_code == status.HTTP_201_CREATED

        proveedor_response = api_client.post(
            reverse("proveedor-list"),
            {
                "contacto": str(contacto.id),
                "giro": "Servicios",
                "dias_credito": 20,
            },
            format="json",
        )
        assert proveedor_response.status_code == status.HTTP_201_CREATED

        assert AuditEvent.all_objects.filter(empresa=empresa, event_type="CLIENTE_CREADO").exists()
        assert AuditEvent.all_objects.filter(empresa=empresa, event_type="PROVEEDOR_CREADO").exists()

    def test_contacto_api_rechaza_campos_maestros_faltantes(self, api_client, admin_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        response = api_client.post(
            reverse("contacto-list"),
            {
                "nombre": "Contacto incompleto",
                "rut": "",
                "tipo": "",
                "email": "",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rut" in response.data["detail"]
        assert "email" in response.data["detail"]
        assert "tipo" in response.data["detail"]
