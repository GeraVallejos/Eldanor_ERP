from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contabilidad.models import AsientoContable, EstadoAsientoContable, PlanCuenta
from apps.contabilidad.services import ContabilidadService
from apps.core.models import UserEmpresa
from apps.core.services.accounting_bridge import AccountingBridge


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario_contabilidad_api(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_contabilidad_api",
        email="owner_contabilidad_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestContabilidadApi:
    def test_seed_plan_base_por_api(self, api_client, owner_usuario_contabilidad_api, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario_contabilidad_api)}")

        response = api_client.post(reverse("plan-cuenta-seed-base"), {}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["created"] == len(ContabilidadService.CODIGOS_BASE)

    def test_crear_asiento_y_contabilizar_por_api(self, api_client, owner_usuario_contabilidad_api, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario_contabilidad_api)}")
        ContabilidadService.seed_plan_base(empresa=empresa, usuario=owner_usuario_contabilidad_api)

        clientes = PlanCuenta.all_objects.get(empresa=empresa, codigo="112100")
        ventas = PlanCuenta.all_objects.get(empresa=empresa, codigo="411100")

        create_resp = api_client.post(
            reverse("asiento-contable-list"),
            {
                "fecha": "2026-03-19",
                "glosa": "Asiento API",
                "movimientos_data": [
                    {"cuenta": str(clientes.id), "debe": "1190", "haber": "0"},
                    {"cuenta": str(ventas.id), "debe": "0", "haber": "1190"},
                ],
            },
            format="json",
        )

        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data
        assert Decimal(str(create_resp.data["total_debe"])) == Decimal("1190.00")

        contabilizar_resp = api_client.post(
            reverse("asiento-contable-contabilizar", args=[create_resp.data["id"]]),
            {},
            format="json",
        )

        assert contabilizar_resp.status_code == status.HTTP_200_OK, contabilizar_resp.data
        assert contabilizar_resp.data["estado"] == EstadoAsientoContable.CONTABILIZADO

    def test_procesar_solicitudes_por_api(self, api_client, owner_usuario_contabilidad_api, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario_contabilidad_api)}")
        ContabilidadService.seed_plan_base(empresa=empresa, usuario=owner_usuario_contabilidad_api)

        AccountingBridge.request_entry(
            empresa=empresa,
            aggregate_type="MovimientoBancario",
            aggregate_id="22222222-2222-2222-2222-222222222222",
            entry_payload={
                "fecha": "2026-03-19",
                "glosa": "Cobro conciliado",
                "referencia_tipo": "MOVIMIENTO_BANCARIO",
                "movimientos": [
                    {"cuenta_codigo": "111200", "debe": "50000", "haber": "0"},
                    {"cuenta_codigo": "112100", "debe": "0", "haber": "50000"},
                ],
            },
            usuario=owner_usuario_contabilidad_api,
            dedup_key="api-accounting-process",
        )

        response = api_client.post(
            reverse("asiento-contable-procesar-solicitudes"),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["processed"] == 1
        assert AsientoContable.all_objects.filter(
            empresa=empresa,
            referencia_tipo="MOVIMIENTO_BANCARIO",
            estado=EstadoAsientoContable.CONTABILIZADO,
        ).exists()
