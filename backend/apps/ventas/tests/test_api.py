from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contactos.models import Cliente, Contacto
from apps.core.models import (
    ConfiguracionTributaria,
    RangoFolioTributario,
    TipoDocumentoTributario,
    UserEmpresa,
)
from apps.productos.models import Impuesto, Producto


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="owner_ventas_api",
        email="owner_ventas_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def cliente(db, empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Cliente Ventas API",
        email="cliente_ventas_api@test.com",
    )
    return Cliente.objects.create(empresa=empresa, contacto=contacto, dias_credito=30)


@pytest.fixture
def impuesto(db, empresa):
    return Impuesto.objects.create(empresa=empresa, nombre="IVA 19%", porcentaje=Decimal("19"))


@pytest.fixture
def producto(db, empresa, impuesto):
    return Producto.objects.create(
        empresa=empresa,
        nombre="Producto Ventas API",
        sku="PV-API-001",
        stock_actual=Decimal("80"),
        maneja_inventario=True,
        precio_referencia=Decimal("1000"),
        impuesto=impuesto,
    )


@pytest.fixture
def rangos_sii(db, empresa, owner_usuario):
    ConfiguracionTributaria.all_objects.create(
        empresa=empresa,
        creado_por=owner_usuario,
        ambiente="CERTIFICACION",
        rut_emisor="76086428-5",
        razon_social="Empresa Test API Tributaria",
        certificado_alias="cert-api",
        certificado_activo=True,
        resolucion_numero=80,
        resolucion_fecha="2026-01-01",
        email_intercambio_dte="dte_api@test.com",
        proveedor_envio="INTERNO",
        activa=True,
    )
    return [
        RangoFolioTributario.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento=TipoDocumentoTributario.FACTURA_VENTA,
            caf_nombre="CAF FACTURAS API",
            folio_desde=100,
            folio_hasta=199,
            fecha_autorizacion="2026-01-01",
            fecha_vencimiento="2026-12-31",
            activo=True,
        ),
        RangoFolioTributario.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento=TipoDocumentoTributario.NOTA_CREDITO_VENTA,
            caf_nombre="CAF NC API",
            folio_desde=200,
            folio_hasta=299,
            fecha_autorizacion="2026-01-01",
            fecha_vencimiento="2026-12-31",
            activo=True,
        ),
    ]


@pytest.mark.django_db
class TestVentasApi:

    def test_flujo_pedido_factura_nota_credito(
        self, api_client, owner_usuario, cliente, producto, impuesto, rangos_sii
    ):
        _ = rangos_sii
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        # 1) Crear pedido
        pedido_resp = api_client.post(
            reverse("pedido-venta-list"),
            {
                "cliente": str(cliente.id),
                "fecha_emision": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert pedido_resp.status_code == status.HTTP_201_CREATED, pedido_resp.data
        pedido_id = pedido_resp.data["id"]

        # 2) Agregar item al pedido
        item_resp = api_client.post(
            reverse("pedido-venta-item-list"),
            {
                "pedido_venta": pedido_id,
                "producto": str(producto.id),
                "cantidad": "2.00",
                "precio_unitario": "1000.00",
                "descuento": "0.00",
                "impuesto": str(impuesto.id),
                "impuesto_porcentaje": "19.00",
            },
            format="json",
        )
        assert item_resp.status_code == status.HTTP_201_CREATED, item_resp.data

        # 3) Confirmar pedido
        confirmar_resp = api_client.post(
            reverse("pedido-venta-confirmar", kwargs={"pk": pedido_id}),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_200_OK, confirmar_resp.data
        assert confirmar_resp.data["estado"] == "CONFIRMADO"

        # 4) Crear factura
        factura_resp = api_client.post(
            reverse("factura-venta-list"),
            {
                "cliente": str(cliente.id),
                "pedido_venta": pedido_id,
                "fecha_emision": str(date.today()),
                "fecha_vencimiento": str(date.today().replace(day=min(date.today().day + 1, 28))),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert factura_resp.status_code == status.HTTP_201_CREATED, factura_resp.data
        factura_id = factura_resp.data["id"]

        # 5) Agregar item a factura
        f_item_resp = api_client.post(
            reverse("factura-venta-item-list"),
            {
                "factura_venta": factura_id,
                "producto": str(producto.id),
                "cantidad": "1.00",
                "precio_unitario": "1000.00",
                "descuento": "0.00",
                "impuesto": str(impuesto.id),
                "impuesto_porcentaje": "19.00",
            },
            format="json",
        )
        assert f_item_resp.status_code == status.HTTP_201_CREATED, f_item_resp.data

        # 6) Emitir factura
        emitir_resp = api_client.post(
            reverse("factura-venta-emitir", kwargs={"pk": factura_id}),
            {},
            format="json",
        )
        assert emitir_resp.status_code == status.HTTP_200_OK, emitir_resp.data
        assert emitir_resp.data["estado"] == "EMITIDA"

        # 7) Anular factura (debe crear NC automática)
        anular_resp = api_client.post(
            reverse("factura-venta-anular", kwargs={"pk": factura_id}),
            {"motivo": "Error de emisión"},
            format="json",
        )
        assert anular_resp.status_code == status.HTTP_200_OK, anular_resp.data
        assert anular_resp.data["estado"] == "ANULADA"

        # 8) Verificar que exista al menos una NC en el listado
        nc_list_resp = api_client.get(reverse("nota-credito-venta-list"))
        assert nc_list_resp.status_code == status.HTTP_200_OK
        assert len(nc_list_resp.data) >= 1

    def test_confirmar_pedido_sin_items_retorna_400(self, api_client, owner_usuario, cliente):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        pedido_resp = api_client.post(
            reverse("pedido-venta-list"),
            {
                "cliente": str(cliente.id),
                "fecha_emision": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert pedido_resp.status_code == status.HTTP_201_CREATED
        pedido_id = pedido_resp.data["id"]

        confirmar_resp = api_client.post(
            reverse("pedido-venta-confirmar", kwargs={"pk": pedido_id}),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_400_BAD_REQUEST
