from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.compras.models import DocumentoCompraProveedor, DocumentoCompraProveedorItem
from apps.contactos.models import Cliente, Contacto, Proveedor
from apps.core.models import UserEmpresa
from apps.inventario.models import StockProducto
from apps.productos.models import ListaPrecio, ListaPrecioItem, Producto
from apps.tesoreria.models import Moneda
from apps.ventas.models import PedidoVenta, PedidoVentaItem


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_productos",
        email="owner_productos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def vendedor_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="vendedor_productos",
        email="vendedor_productos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="VENDEDOR", activo=True)
    return user


@pytest.fixture
def proveedor(db, empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Proveedor Productos API",
        rut="10111222-5",
        email="proveedor_productos@test.com",
    )
    return Proveedor.objects.create(empresa=empresa, contacto=contacto)


@pytest.mark.django_db
class TestProductoApi:
    def test_crear_producto_ignora_stock_operativo_en_crud_normal(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        resp = api_client.post(
            reverse("producto-list"),
            {
                "nombre": "Producto Front Resumen",
                "sku": "PFR-001",
                "tipo": "PRODUCTO",
                "precio_referencia": "10000",
                "precio_costo": "7000",
                "maneja_inventario": True,
                "stock_actual": "5",
                "activo": True,
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED, resp.data

        producto = Producto.all_objects.get(id=resp.data["id"])
        assert Decimal(str(producto.stock_actual)) == Decimal("0")
        assert Decimal(str(producto.costo_promedio)) == Decimal("7000")
        assert Decimal(str(resp.data["costo_promedio"])) == Decimal("7000")
        assert not StockProducto.all_objects.filter(empresa=empresa, producto=producto).exists()

    def test_crear_producto_ignora_campos_operativos_read_only(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        resp = api_client.post(
            reverse("producto-list"),
            {
                "nombre": "Producto Read Only",
                "sku": "PRO-RO-001",
                "tipo": "PRODUCTO",
                "precio_referencia": "1000",
                "costo_promedio": "999.9999",
                "activo": True,
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        producto = Producto.all_objects.get(id=resp.data["id"])
        assert Decimal(str(producto.costo_promedio)) == Decimal("0")
        assert Decimal(str(producto.stock_actual)) == Decimal("0")
        assert resp.data["costo_promedio"] in {"0.0000", "0"}

    def test_listado_productos_oculta_inactivos_por_defecto(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        Producto.objects.create(
            empresa=empresa,
            nombre="Producto Activo",
            sku="PA-001",
            precio_referencia=Decimal("1200"),
            activo=True,
        )
        Producto.objects.create(
            empresa=empresa,
            nombre="Producto Inactivo",
            sku="PI-001",
            precio_referencia=Decimal("1300"),
            activo=False,
        )

        resp = api_client.get(reverse("producto-list"))

        assert resp.status_code == status.HTTP_200_OK
        nombres = {item["nombre"].upper() for item in resp.data}
        assert "PRODUCTO ACTIVO" in nombres
        assert "PRODUCTO INACTIVO" not in nombres

    def test_owner_puede_listar_inactivos_con_include_inactive(
        self,
        api_client,
        owner_usuario,
        empresa,
    ):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        Producto.objects.create(
            empresa=empresa,
            nombre="Producto Activo Owner",
            sku="PAO-001",
            precio_referencia=Decimal("1200"),
            activo=True,
        )
        Producto.objects.create(
            empresa=empresa,
            nombre="Producto Inactivo Owner",
            sku="PIO-001",
            precio_referencia=Decimal("1300"),
            activo=False,
        )

        resp = api_client.get(reverse("producto-list"), {"include_inactive": "1"})

        assert resp.status_code == status.HTTP_200_OK
        nombres = {item["nombre"].upper() for item in resp.data}
        assert "PRODUCTO ACTIVO OWNER" in nombres
        assert "PRODUCTO INACTIVO OWNER" in nombres

    def test_usuario_no_avanzado_no_puede_listar_inactivos(
        self,
        api_client,
        vendedor_usuario,
        empresa,
    ):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(vendedor_usuario)}")

        Producto.objects.create(
            empresa=empresa,
            nombre="Producto Activo Vendedor",
            sku="PAV-001",
            precio_referencia=Decimal("1200"),
            activo=True,
        )
        Producto.objects.create(
            empresa=empresa,
            nombre="Producto Inactivo Vendedor",
            sku="PIV-001",
            precio_referencia=Decimal("1300"),
            activo=False,
        )

        resp = api_client.get(reverse("producto-list"), {"include_inactive": "1"})

        assert resp.status_code == status.HTTP_200_OK
        nombres = {item["nombre"].upper() for item in resp.data}
        assert "PRODUCTO ACTIVO VENDEDOR" in nombres
        assert "PRODUCTO INACTIVO VENDEDOR" not in nombres

    def test_delete_producto_sin_referencias_elimina(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Sin Uso",
            sku="PSU-001",
            precio_referencia=Decimal("1200"),
        )

        resp = api_client.delete(reverse("producto-detail", args=[producto.id]))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Producto.all_objects.filter(id=producto.id).exists()

    def test_delete_producto_con_referencias_lo_anula(self, api_client, owner_usuario, empresa, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Con Historial",
            sku="PCH-001",
            precio_referencia=Decimal("2500"),
        )

        documento = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor,
            folio="FAC-PROD-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("7500"),
            impuestos=Decimal("0"),
            total=Decimal("7500"),
        )
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=documento,
            producto=producto,
            cantidad=Decimal("3.00"),
            precio_unitario=Decimal("2500"),
            subtotal=Decimal("7500"),
        )

        resp = api_client.delete(reverse("producto-detail", args=[producto.id]))

        assert resp.status_code == status.HTTP_204_NO_CONTENT
        producto.refresh_from_db()
        assert producto.activo is False

    def test_owner_puede_reactivar_producto_inactivo_por_patch_detalle(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Reactivable",
            sku="PR-001",
            precio_referencia=Decimal("2200"),
            activo=False,
        )

        resp = api_client.patch(
            reverse("producto-detail", args=[producto.id]),
            {"activo": True},
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        producto.refresh_from_db()
        assert producto.activo is True

    def test_trazabilidad_producto_resume_listas_documentos_y_alertas(
        self,
        api_client,
        owner_usuario,
        empresa,
        proveedor,
    ):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        moneda_base = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        cliente_contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Trazabilidad",
            rut="11111111-1",
            email="cliente_trazabilidad@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=cliente_contacto)

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Trazable",
            sku="PTR-001",
            precio_referencia=Decimal("4900"),
            maneja_inventario=True,
            stock_minimo=Decimal("0"),
        )

        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Lista Cliente Norte",
            moneda=moneda_base,
            cliente=cliente,
            fecha_desde=date.today(),
            activa=True,
            prioridad=10,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            lista=lista,
            producto=producto,
            precio=Decimal("4500"),
            descuento_maximo=Decimal("5"),
        )

        pedido = PedidoVenta.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            cliente=cliente,
            numero="PV-TRAZA-001",
            fecha_emision=date.today(),
            estado="CONFIRMADO",
            subtotal=Decimal("9000"),
            impuestos=Decimal("0"),
            total=Decimal("9000"),
            lista_precio=lista,
        )
        PedidoVentaItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            pedido_venta=pedido,
            producto=producto,
            descripcion="Producto trazable",
            cantidad=Decimal("2"),
            precio_unitario=Decimal("4500"),
            subtotal=Decimal("9000"),
            total=Decimal("9000"),
        )

        documento = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor,
            folio="FAC-TRAZA-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("7500"),
            impuestos=Decimal("0"),
            total=Decimal("7500"),
            moneda=moneda_base,
        )
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=documento,
            producto=producto,
            cantidad=Decimal("3.00"),
            precio_unitario=Decimal("2500"),
            subtotal=Decimal("7500"),
        )

        resp = api_client.get(reverse("producto-trazabilidad", args=[producto.id]))

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["resumen"]["listas_configuradas"] == 1
        assert resp.data["resumen"]["listas_activas_vigentes"] == 1
        assert resp.data["resumen"]["pedidos_venta"] == 1
        assert resp.data["resumen"]["documentos_compra"] == 1
        assert resp.data["listas_precio"][0]["nombre"] == "Lista Cliente Norte"
        assert resp.data["listas_precio"][0]["cliente_nombre"] == "CLIENTE TRAZABILIDAD"
        assert resp.data["uso_documentos"]["pedidos_venta"]["ultimos"][0]["numero"] == "PV-TRAZA-001"
        assert resp.data["uso_documentos"]["documentos_compra"]["ultimos"][0]["folio"] == "FAC-TRAZA-001"
        alert_codes = {item["codigo"] for item in resp.data["alertas"]}
        assert "SIN_CATEGORIA" in alert_codes
        assert "SIN_IMPUESTO" in alert_codes
        assert "SIN_STOCK_MINIMO" in alert_codes


