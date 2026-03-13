from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contactos.models import Cliente, Contacto
from apps.core.models import Moneda, UserEmpresa


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_finanzas_api",
        email="owner_finanzas_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestFinanzasApi:
    def test_tipos_cambio_convertir_endpoint(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        usd = Moneda.all_objects.get(empresa=empresa, codigo="USD")
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        create_resp = api_client.post(
            reverse("tipo-cambio-list"),
            {
                "moneda_origen": str(usd.id),
                "moneda_destino": str(clp.id),
                "fecha": "2026-03-12",
                "tasa": "950",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data

        convert_resp = api_client.post(
            reverse("tipo-cambio-convertir"),
            {
                "monto": "10",
                "moneda_origen": "USD",
                "moneda_destino": "CLP",
                "fecha": "2026-03-12",
            },
            format="json",
        )
        assert convert_resp.status_code == status.HTTP_200_OK, convert_resp.data
        assert Decimal(str(convert_resp.data["monto_convertido"])) == Decimal("9500")

    def test_cuentas_por_cobrar_crear_y_aplicar_pago(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente API Finanzas",
            rut="12312312-3",
            email="cliente_finanzas_api@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        create_resp = api_client.post(
            reverse("cuenta-por-cobrar-list"),
            {
                "cliente": str(cliente.id),
                "moneda": str(clp.id),
                "referencia": "CXC-API-001",
                "fecha_emision": "2026-03-12",
                "fecha_vencimiento": "2026-03-30",
                "monto_total": "100000",
                "saldo": "100000",
                "estado": "PENDIENTE",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data

        pago_resp = api_client.post(
            reverse("cuenta-por-cobrar-aplicar-pago", args=[create_resp.data["id"]]),
            {
                "monto": "25000",
                "fecha_pago": "2026-03-15",
            },
            format="json",
        )
        assert pago_resp.status_code == status.HTTP_200_OK, pago_resp.data
        assert Decimal(str(pago_resp.data["saldo"])) == Decimal("75000")
        assert pago_resp.data["estado"] == "PARCIAL"
