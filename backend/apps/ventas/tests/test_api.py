from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contactos.models import Cliente, Contacto
from apps.core.models import UserEmpresa
from apps.facturacion.models import ConfiguracionTributaria, RangoFolioTributario, TipoDocumentoTributario
from apps.productos.models import Impuesto, Producto
from apps.ventas.models import (
    EstadoPedidoVenta,
    EstadoFacturaVenta,
    EstadoGuiaDespacho,
    EstadoNotaCreditoVenta,
    FacturaVenta,
    FacturaVentaItem,
    GuiaDespacho,
    NotaCreditoVenta,
    PedidoVenta,
)


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
def vendedor_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="vendedor_ventas_api",
        email="vendedor_ventas_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="VENDEDOR", activo=True)
    return user


@pytest.fixture
def usuario_sin_permisos_ventas(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="sin_permiso_ventas_api",
        email="sin_permiso_ventas_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="BODEGA", activo=True)
    return user


@pytest.fixture
def cliente(db, empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Cliente Ventas API",
        email="cliente_ventas_api@test.com",
        rut="12.345.678-5",
        tipo="EMPRESA",
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

    def test_resumen_operativo_facturas_retorna_metricas(self, api_client, owner_usuario, cliente):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            cliente=cliente,
            numero="FV-R-001",
            fecha_emision=date(2026, 3, 1),
            fecha_vencimiento=date(2026, 3, 10),
            estado=EstadoFacturaVenta.EMITIDA,
            total=Decimal("119000.00"),
        )
        FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            cliente=cliente,
            numero="FV-R-002",
            fecha_emision=date(2026, 3, 15),
            fecha_vencimiento=date(2026, 3, 25),
            estado=EstadoFacturaVenta.BORRADOR,
            total=Decimal("59500.00"),
        )
        FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            cliente=cliente,
            numero="FV-R-003",
            fecha_emision=date(2026, 3, 18),
            fecha_vencimiento=date(2026, 3, 22),
            estado=EstadoFacturaVenta.ANULADA,
            total=Decimal("30000.00"),
        )

        response = api_client.get(reverse("factura-venta-resumen-operativo"))

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["total_documentos"] == 3
        assert response.data["emitidas"] == 1
        assert response.data["borradores"] == 1
        assert response.data["anuladas"] == 1
        assert Decimal(str(response.data["monto_total"])) == Decimal("208500.00")
        assert Decimal(str(response.data["monto_vencido"])) == Decimal("119000.00")
        assert Decimal(str(response.data["monto_por_vencer_7_dias"])) == Decimal("0.00")

    def test_resumen_operativo_facturas_rechaza_usuario_sin_permiso(self, api_client, usuario_sin_permisos_ventas):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(usuario_sin_permisos_ventas)}")

        response = api_client.get(reverse("factura-venta-resumen-operativo"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error_code"] == "PERMISSION_DENIED"

    def test_analytics_facturas_retorna_series_top_y_vencidos(self, api_client, owner_usuario, cliente, producto, impuesto):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        factura = FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="FV-A-001",
            cliente=cliente,
            estado=EstadoFacturaVenta.EMITIDA,
            fecha_emision=date(2026, 3, 1),
            fecha_vencimiento=date(2026, 3, 5),
            total=Decimal("119000.00"),
        )
        FacturaVentaItem.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            factura_venta=factura,
            producto=producto,
            descripcion="Producto Analitica Ventas",
            cantidad=Decimal("2.00"),
            precio_unitario=Decimal("59500.00"),
            descuento=Decimal("0.00"),
            impuesto=impuesto,
            impuesto_porcentaje=Decimal("19.00"),
            subtotal=Decimal("119000.00"),
        )

        response = api_client.get(reverse("factura-venta-analytics"), {"agrupacion": "mensual"})

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["metrics"]["total_facturas"] == 1
        assert len(response.data["series"]) == 1
        assert response.data["top_clientes"][0]["nombre"] == "CLIENTE VENTAS API"
        assert response.data["top_productos"][0]["nombre"] == "Producto Analitica Ventas"
        assert response.data["documentos_vencidos"][0]["numero"] == "FV-A-001"

    def test_acciones_custom_ventas_rechazan_vendedor_sin_permiso_operativo(
        self, api_client, owner_usuario, vendedor_usuario, cliente, producto, impuesto, rangos_sii
    ):
        _ = rangos_sii
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
        assert pedido_resp.status_code == status.HTTP_201_CREATED, pedido_resp.data
        pedido_id = pedido_resp.data["id"]

        pedido_item = api_client.post(
            reverse("pedido-venta-item-list"),
            {
                "pedido_venta": pedido_id,
                "producto": str(producto.id),
                "cantidad": "1.00",
                "precio_unitario": "1000.00",
                "descuento": "0.00",
                "impuesto": str(impuesto.id),
                "impuesto_porcentaje": "19.00",
            },
            format="json",
        )
        assert pedido_item.status_code == status.HTTP_201_CREATED, pedido_item.data

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

        factura_item = api_client.post(
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
        assert factura_item.status_code == status.HTTP_201_CREATED, factura_item.data

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(vendedor_usuario)}")

        confirmar_pedido = api_client.post(reverse("pedido-venta-confirmar", kwargs={"pk": pedido_id}), {}, format="json")
        assert confirmar_pedido.status_code == status.HTTP_403_FORBIDDEN, confirmar_pedido.data
        assert confirmar_pedido.data["error_code"] == "PERMISSION_DENIED"

        emitir_factura = api_client.post(reverse("factura-venta-emitir", kwargs={"pk": factura_id}), {}, format="json")
        assert emitir_factura.status_code == status.HTTP_403_FORBIDDEN, emitir_factura.data
        assert emitir_factura.data["error_code"] == "PERMISSION_DENIED"

        anular_factura = api_client.post(
            reverse("factura-venta-anular", kwargs={"pk": factura_id}),
            {"motivo": "Sin permiso"},
            format="json",
        )
        assert anular_factura.status_code == status.HTTP_403_FORBIDDEN, anular_factura.data
        assert anular_factura.data["error_code"] == "PERMISSION_DENIED"

    def test_patch_guia_confirmada_retorna_conflict(self, api_client, owner_usuario, cliente):
        guia = GuiaDespacho.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="GD-LOCK-001",
            cliente=cliente,
            estado=EstadoGuiaDespacho.CONFIRMADA,
            fecha_despacho=date.today(),
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        response = api_client.patch(
            reverse("guia-despacho-detail", kwargs={"pk": guia.id}),
            {"observaciones": "Intento editar confirmada"},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error_code"] == "CONFLICT"

    def test_patch_factura_emitida_retorna_conflict(self, api_client, owner_usuario, cliente):
        factura = FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="FV-LOCK-001",
            cliente=cliente,
            estado=EstadoFacturaVenta.EMITIDA,
            fecha_emision=date.today(),
            fecha_vencimiento=date.today(),
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        response = api_client.patch(
            reverse("factura-venta-detail", kwargs={"pk": factura.id}),
            {"observaciones": "Intento editar emitida"},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error_code"] == "CONFLICT"

    def test_patch_nota_emitida_retorna_conflict(self, api_client, owner_usuario, cliente):
        factura_origen = FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="FV-ORIG-001",
            cliente=cliente,
            estado=EstadoFacturaVenta.EMITIDA,
            fecha_emision=date.today(),
            fecha_vencimiento=date.today(),
        )
        nota = NotaCreditoVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="NC-LOCK-001",
            factura_origen=factura_origen,
            cliente=cliente,
            estado=EstadoNotaCreditoVenta.EMITIDA,
            fecha_emision=date.today(),
            motivo="Ajuste emitido",
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        response = api_client.patch(
            reverse("nota-credito-venta-detail", kwargs={"pk": nota.id}),
            {"motivo": "Intento editar emitida"},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error_code"] == "CONFLICT"

    def test_delete_pedido_confirmado_retorna_conflict(self, api_client, owner_usuario, cliente):
        pedido = PedidoVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="PV-DEL-001",
            cliente=cliente,
            fecha_emision=date.today(),
            estado=EstadoPedidoVenta.CONFIRMADO,
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        response = api_client.delete(
            reverse("pedido-venta-detail", kwargs={"pk": pedido.id}),
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error_code"] == "CONFLICT"

    def test_anular_factura_borrador_retorna_conflict(self, api_client, owner_usuario, cliente):
        factura = FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="FV-ANU-001",
            cliente=cliente,
            estado=EstadoFacturaVenta.BORRADOR,
            fecha_emision=date.today(),
            fecha_vencimiento=date.today(),
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        response = api_client.post(
            reverse("factura-venta-anular", kwargs={"pk": factura.id}),
            {"motivo": "No deberia anular borrador"},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error_code"] == "CONFLICT"

    def test_anular_nota_borrador_retorna_conflict(self, api_client, owner_usuario, cliente):
        factura_origen = FacturaVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="FV-ORIG-ANU-001",
            cliente=cliente,
            estado=EstadoFacturaVenta.EMITIDA,
            fecha_emision=date.today(),
            fecha_vencimiento=date.today(),
        )
        nota = NotaCreditoVenta.all_objects.create(
            empresa=owner_usuario.empresa_activa,
            creado_por=owner_usuario,
            numero="NC-ANU-001",
            factura_origen=factura_origen,
            cliente=cliente,
            estado=EstadoNotaCreditoVenta.BORRADOR,
            fecha_emision=date.today(),
            motivo="Ajuste borrador",
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        response = api_client.post(
            reverse("nota-credito-venta-anular", kwargs={"pk": nota.id}),
            {"motivo": "No deberia anular borrador"},
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT, response.data
        assert response.data["error_code"] == "CONFLICT"
