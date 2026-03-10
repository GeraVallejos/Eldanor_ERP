from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.compras.models import OrdenCompra
from apps.contactos.models import Contacto, Proveedor
from apps.core.models import UserEmpresa
from apps.inventario.models import MovimientoInventario
from apps.productos.models import Producto


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="owner_compras",
        email="owner_compras@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def proveedor(db, empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Proveedor Compras",
        rut="11222333-4",
        email="proveedor@test.com",
    )
    return Proveedor.objects.create(empresa=empresa, contacto=contacto)


@pytest.mark.django_db
class TestComprasApi:
    def test_crear_orden_compra(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        payload = {
            "proveedor": str(proveedor.id),
            "numero": "OC-0001",
            "fecha_emision": str(date.today()),
            "estado": "BORRADOR",
        }

        resp = api_client.post(reverse("orden-compra-list"), payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["numero"] == "OC-0001"

    def test_confirmar_recepcion_genera_movimiento_inventario(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Compra API",
            sku="PC-API-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        orden = OrdenCompra.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            proveedor=proveedor,
            numero="OC-0002",
            fecha_emision=date.today(),
            estado="ENVIADA",
        )

        orden_item_resp = api_client.post(
            reverse("orden-compra-item-list"),
            {
                "orden_compra": str(orden.id),
                "producto": str(producto.id),
                "descripcion": "Item OC",
                "cantidad": "5.00",
                "precio_unitario": "1000.00",
                "subtotal": "5000.00",
                "total": "5000.00",
            },
            format="json",
        )
        assert orden_item_resp.status_code == status.HTTP_201_CREATED

        recepcion_resp = api_client.post(
            reverse("recepcion-compra-list"),
            {
                "orden_compra": str(orden.id),
                "fecha": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert recepcion_resp.status_code == status.HTTP_201_CREATED

        recepcion_id = recepcion_resp.data["id"]

        recepcion_item_resp = api_client.post(
            reverse("recepcion-compra-item-list"),
            {
                "recepcion": recepcion_id,
                "orden_item": orden_item_resp.data["id"],
                "producto": str(producto.id),
                "cantidad": "5.00",
            },
            format="json",
        )
        assert recepcion_item_resp.status_code == status.HTTP_201_CREATED

        confirmar_resp = api_client.post(
            reverse("recepcion-compra-confirmar", args=[recepcion_id]),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_200_OK
        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            producto=producto,
            documento_tipo="COMPRA_RECEPCION",
        ).exists()
