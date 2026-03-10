from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Producto


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="owner_inventario_api",
        email="owner_inventario_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestInventarioApi:
    def test_kardex_endpoint_devuelve_movimientos(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Kardex API",
            sku="PK-API-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            referencia="KARDEX-TEST",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(reverse("movimiento-inventario-kardex"), {"producto_id": str(producto.id)})

        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_snapshot_endpoint_devuelve_ultimo_snapshot(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Snapshot API",
            sku="PS-API-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("2000"),
        )

        mov = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("3.00"),
            referencia="SNAPSHOT-TEST",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(
            reverse("movimiento-inventario-snapshot"),
            {"producto_id": str(producto.id), "bodega_id": str(mov.bodega_id)},
        )

        assert resp.status_code == status.HTTP_200_OK
        assert str(resp.data["producto"]) == str(producto.id)
