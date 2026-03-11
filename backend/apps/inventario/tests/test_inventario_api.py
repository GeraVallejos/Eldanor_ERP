from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Categoria, Producto


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
    def test_resumen_excluye_productos_inactivos(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Inactivo Resumen",
            sku="PIR-0001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
            activo=True,
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            costo_unitario=Decimal("1000.00"),
            referencia="RESUMEN-INACTIVO",
            empresa=empresa,
            usuario=owner_usuario,
        )

        producto.activo = False
        producto.save(skip_clean=True, update_fields=["activo"])

        resp_producto = api_client.get(reverse("stock-producto-resumen"), {"group_by": "producto"})
        assert resp_producto.status_code == status.HTTP_200_OK
        ids_producto = {str(item.get("producto_id")) for item in resp_producto.data.get("detalle", [])}
        assert str(producto.id) not in ids_producto

        resp_bodega = api_client.get(reverse("stock-producto-resumen"), {"group_by": "bodega"})
        assert resp_bodega.status_code == status.HTTP_200_OK
        assert Decimal(str(resp_bodega.data["totales"]["stock_total"])) == Decimal("0")

    def test_resumen_producto_incluye_productos_sin_stock(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Sin Stock Resumen",
            sku="PSR-0001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1500"),
        )

        resp = api_client.get(reverse("stock-producto-resumen"), {"group_by": "producto"})

        assert resp.status_code == status.HTTP_200_OK
        detalle = resp.data.get("detalle", [])
        row = next((item for item in detalle if str(item.get("producto_id")) == str(producto.id)), None)
        assert row is not None
        assert Decimal(str(row.get("stock_total", 0))) == Decimal("0")

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

    def test_kardex_endpoint_permita_filtros_y_paginacion(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Filtros Kardex",
            sku="PK-FILT-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1500"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            referencia="COMPRA TEST UNO",
            empresa=empresa,
            usuario=owner_usuario,
            documento_tipo=TipoDocumentoReferencia.COMPRA_RECEPCION,
        )
        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="SALIDA",
            cantidad=Decimal("1.00"),
            referencia="VENTA TEST DOS",
            empresa=empresa,
            usuario=owner_usuario,
            documento_tipo=TipoDocumentoReferencia.VENTA_FACTURA,
        )

        resp = api_client.get(
            reverse("movimiento-inventario-kardex"),
            {
                "producto_id": str(producto.id),
                "tipo": "ENTRADA",
                "documento_tipo": TipoDocumentoReferencia.COMPRA_RECEPCION,
                "referencia": "COMPRA",
                "page_size": 1,
            },
        )

        assert resp.status_code == status.HTTP_200_OK
        assert "count" in resp.data
        assert len(resp.data["results"]) == 1
        assert resp.data["results"][0]["tipo"] == "ENTRADA"

    def test_resumen_valorizado_endpoint(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        categoria = Categoria.objects.create(
            empresa=empresa,
            nombre="Herramientas",
            descripcion="Categoria test",
            activa=True,
        )

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Resumen",
            sku="PR-RES-1",
            categoria=categoria,
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("2500"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("4.00"),
            costo_unitario=Decimal("1000.00"),
            referencia="RESUMEN-TEST",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(reverse("stock-producto-resumen"), {"group_by": "producto"})

        assert resp.status_code == status.HTTP_200_OK
        assert "totales" in resp.data
        assert Decimal(str(resp.data["totales"]["stock_total"])) > 0
        assert len(resp.data.get("detalle", [])) > 0
        assert resp.data["detalle"][0].get("producto__categoria__nombre") == "HERRAMIENTAS"
