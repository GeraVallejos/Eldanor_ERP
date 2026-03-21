from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contactos.models import Cliente, Contacto
from apps.core.models import UserEmpresa
from apps.tesoreria.models import Moneda
from apps.tesoreria.services import TipoCambioService
from apps.productos.models import ListaPrecio, ListaPrecioItem, Producto


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_precio_api",
        email="owner_precio_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestPrecioApi:
    def test_producto_precio_endpoint_resuelve_lista_y_conversion(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Producto Precio API",
            sku="PPA-001",
            precio_referencia=Decimal("10000"),
        )
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Precio API",
            rut="14141414-3",
            email="cliente_precio_api@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)

        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        usd = Moneda.all_objects.get(empresa=empresa, codigo="USD")
        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Lista API",
            moneda=clp,
            cliente=cliente,
            fecha_desde=date(2026, 1, 1),
            activa=True,
            prioridad=10,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            lista=lista,
            producto=producto,
            precio=Decimal("9500"),
        )
        TipoCambioService.registrar_tipo_cambio(
            empresa=empresa,
            moneda_origen=clp,
            moneda_destino=usd,
            fecha=date(2026, 3, 1),
            tasa=Decimal("0.001"),
            usuario=owner_usuario,
        )

        resp = api_client.get(
            reverse("producto-precio", args=[producto.id]),
            {
                "cliente_id": str(cliente.id),
                "moneda": "USD",
                "fecha": "2026-03-12",
            },
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["fuente"] == "LISTA_PRECIO"
        assert resp.data["moneda"] == "USD"
        assert Decimal(str(resp.data["precio"])) == Decimal("9.50")


