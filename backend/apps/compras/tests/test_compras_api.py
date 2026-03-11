from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.compras.models import OrdenCompra
from apps.contactos.models import Contacto, Proveedor
from apps.core.models import SecuenciaDocumento, TipoDocumento, UserEmpresa
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
            "fecha_emision": str(date.today()),
            "estado": "BORRADOR",
        }

        resp = api_client.post(reverse("orden-compra-list"), payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["numero"]

    def test_crear_orden_reintenta_si_numero_ya_existe(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        # Simula secuencia desfasada: apunta al siguiente numero ya ocupado.
        SecuenciaDocumento.all_objects.update_or_create(
            empresa=empresa,
            tipo_documento=TipoDocumento.ORDEN_COMPRA,
            defaults={"ultimo_numero": 0, "prefijo": "ORD", "padding": 5},
        )

        OrdenCompra.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            proveedor=proveedor,
            numero="ORD-00001",
            fecha_emision=date.today(),
            estado="BORRADOR",
        )

        payload = {
            "proveedor": str(proveedor.id),
            "fecha_emision": str(date.today()),
            "estado": "BORRADOR",
        }

        resp = api_client.post(reverse("orden-compra-list"), payload, format="json")

        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["numero"] == "ORD-00002"

    def test_confirmar_guia_genera_movimiento_inventario(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Compra API",
            sku="PC-API-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "GUIA_RECEPCION",
                "proveedor": str(proveedor.id),
                "folio": "GR-API-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED

        documento_id = documento_resp.data["id"]

        documento_item_resp = api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": documento_id,
                "producto": str(producto.id),
                "cantidad": "5.00",
                "precio_unitario": "1000.00",
                "subtotal": "5000.00",
            },
            format="json",
        )
        assert documento_item_resp.status_code == status.HTTP_201_CREATED, documento_item_resp.data

        confirmar_resp = api_client.post(
            reverse("documento-compra-confirmar-guia", args=[documento_id]),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_200_OK
        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            producto=producto,
            documento_tipo="GUIA_RECEPCION",
        ).exists()

    def test_confirmar_factura_sin_guia_previa_mueve_inventario(self, api_client, owner_usuario, proveedor, empresa):
        # Chile: muchos proveedores emiten solo factura (sin guia de despacho).
        # En ese caso la factura actua como documento de entrada y debe mover inventario.
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Sin OC",
            sku="PSO-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1200"),
        )

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "folio": "FAC-API-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
                "observaciones": "Factura de compra API",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED

        documento_id = documento_resp.data["id"]

        documento_item_resp = api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": documento_id,
                "producto": str(producto.id),
                "cantidad": "3.00",
                "precio_unitario": "1500.00",
                "subtotal": "4500.00",
            },
            format="json",
        )
        assert documento_item_resp.status_code == status.HTTP_201_CREATED, documento_item_resp.data

        confirmar_resp = api_client.post(
            reverse("documento-compra-confirmar-factura", args=[documento_id]),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_200_OK
        assert confirmar_resp.data["estado"] == "CONFIRMADO"
        # Sin guia ni recepcion previa: la factura SI mueve inventario
        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            producto=producto,
            documento_tipo="FACTURA_COMPRA",
        ).exists()
        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("3.00")

    def test_permite_multiples_documentos_para_misma_oc(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {
                "proveedor": str(proveedor.id),
                "fecha_emision": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED, orden_resp.data
        orden_id = orden_resp.data["id"]

        primer_doc = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "GUIA_RECEPCION",
                "proveedor": str(proveedor.id),
                "orden_compra": str(orden_id),
                "folio": "GR-OC-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert primer_doc.status_code == status.HTTP_201_CREATED, primer_doc.data

        segundo_doc = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "orden_compra": str(orden_id),
                "folio": "FAC-OC-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert segundo_doc.status_code == status.HTTP_201_CREATED, segundo_doc.data

    def test_no_permite_anular_oc_con_documento_activo_asociado(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {
                "proveedor": str(proveedor.id),
                "fecha_emision": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED, orden_resp.data
        orden_id = orden_resp.data["id"]

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "orden_compra": str(orden_id),
                "folio": "FAC-OC-BLOCK-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED, documento_resp.data

        anular_resp = api_client.post(reverse("orden-compra-anular", args=[orden_id]), {}, format="json")
        assert anular_resp.status_code == status.HTTP_409_CONFLICT

        orden = OrdenCompra.all_objects.get(id=orden_id)
        assert orden.estado != "CANCELADA"

    def test_no_permite_corregir_oc_con_documento_activo_asociado(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {
                "proveedor": str(proveedor.id),
                "fecha_emision": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED, orden_resp.data
        orden_id = orden_resp.data["id"]

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "orden_compra": str(orden_id),
                "folio": "FAC-OC-CORR-BLOCK-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED, documento_resp.data

        corregir_resp = api_client.post(
            reverse("orden-compra-corregir", args=[orden_id]),
            {"motivo": "Ajuste de cantidades"},
            format="json",
        )
        assert corregir_resp.status_code == status.HTTP_409_CONFLICT

        orden = OrdenCompra.all_objects.get(id=orden_id)
        assert orden.estado == "ENVIADA"

    def test_duplicar_oc_preserva_totales(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {
                "proveedor": str(proveedor.id),
                "fecha_emision": str(date.today()),
                "estado": "BORRADOR",
                "subtotal": "10000.00",
                "impuestos": "1900.00",
                "total": "11900.00",
            },
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED, orden_resp.data
        orden_id = orden_resp.data["id"]

        duplicar_resp = api_client.post(reverse("orden-compra-duplicar", args=[orden_id]), {}, format="json")
        assert duplicar_resp.status_code == status.HTTP_201_CREATED, duplicar_resp.data
        assert duplicar_resp.data["id"] != orden_id
        assert str(duplicar_resp.data["subtotal"]) in {"10000.00", "10000"}
        assert str(duplicar_resp.data["impuestos"]) in {"1900.00", "1900"}
        assert str(duplicar_resp.data["total"]) in {"11900.00", "11900"}

    def test_no_permite_editar_oc_no_borrador(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {"proveedor": str(proveedor.id), "fecha_emision": str(date.today()), "estado": "BORRADOR"},
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED
        orden_id = orden_resp.data["id"]

        # Enviar la orden (pasa a ENVIADA)
        OrdenCompra.all_objects.filter(id=orden_id).update(estado="ENVIADA")

        # Intentar PATCH sobre una OC ENVIADA → debe fallar con 409
        patch_resp = api_client.patch(
            reverse("orden-compra-detail", args=[orden_id]),
            {"observaciones": "modificacion no permitida"},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_409_CONFLICT

    def test_crear_documento_avanza_oc_borrador_a_enviada(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {"proveedor": str(proveedor.id), "fecha_emision": str(date.today()), "estado": "BORRADOR"},
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED
        orden_id = orden_resp.data["id"]
        assert orden_resp.data["estado"] == "BORRADOR"

        # Crear un documento de compra referenciando la OC en BORRADOR
        doc_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "folio": "FAC-AUTO-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
                "orden_compra": str(orden_id),
            },
            format="json",
        )
        assert doc_resp.status_code == status.HTTP_201_CREATED, doc_resp.data

        # La OC debe haber avanzado a ENVIADA automáticamente
        orden_actualizada = OrdenCompra.all_objects.get(id=orden_id)
        assert orden_actualizada.estado == "ENVIADA"

        # Y ya no se puede editar la OC
        patch_resp = api_client.patch(
            reverse("orden-compra-detail", args=[orden_id]),
            {"observaciones": "no deberia poder"},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_409_CONFLICT

    def test_no_permite_editar_documento_confirmado(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "folio": "FAC-LOCK-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED
        documento_id = documento_resp.data["id"]

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Lock",
            sku="PLK-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )
        item_resp = api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": documento_id,
                "producto": str(producto.id),
                "cantidad": "1.00",
                "precio_unitario": "1000.00",
                "subtotal": "1000.00",
            },
            format="json",
        )
        assert item_resp.status_code == status.HTTP_201_CREATED, item_resp.data

        confirmar_resp = api_client.post(
            reverse("documento-compra-confirmar-factura", args=[documento_id]),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_200_OK

        patch_resp = api_client.patch(
            reverse("documento-compra-detail", args=[documento_id]),
            {"observaciones": "Intento editar confirmado"},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_409_CONFLICT

    def test_corregir_documento_confirmado_crea_borrador(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "GUIA_RECEPCION",
                "proveedor": str(proveedor.id),
                "folio": "GR-CORR-API-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED
        documento_id = documento_resp.data["id"]

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Corregir",
            sku="PCOR-API-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("2000"),
        )
        item_resp = api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": documento_id,
                "producto": str(producto.id),
                "cantidad": "2.00",
                "precio_unitario": "2000.00",
                "subtotal": "4000.00",
            },
            format="json",
        )
        assert item_resp.status_code == status.HTTP_201_CREATED, item_resp.data

        confirmar_resp = api_client.post(
            reverse("documento-compra-confirmar-guia", args=[documento_id]),
            {},
            format="json",
        )
        assert confirmar_resp.status_code == status.HTTP_200_OK

        corregir_resp = api_client.post(
            reverse("documento-compra-corregir", args=[documento_id]),
            {"motivo": "Error de digitacion"},
            format="json",
        )
        assert corregir_resp.status_code == status.HTTP_200_OK
        assert corregir_resp.data["estado"] == "BORRADOR"
        assert corregir_resp.data["motivo_correccion"] == "Error de digitacion"
        assert str(corregir_resp.data["documento_origen"]) == documento_id

    def test_listado_items_documento_filtra_por_query_param(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto_a = Producto.objects.create(
            empresa=empresa,
            nombre="Producto A",
            sku="PA-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )
        producto_b = Producto.objects.create(
            empresa=empresa,
            nombre="Producto B",
            sku="PB-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("2000"),
        )

        doc_a = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "folio": "FAC-FLT-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert doc_a.status_code == status.HTTP_201_CREATED

        doc_b = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "folio": "FAC-FLT-002",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "BORRADOR",
            },
            format="json",
        )
        assert doc_b.status_code == status.HTTP_201_CREATED

        item_a = api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": doc_a.data["id"],
                "producto": str(producto_a.id),
                "cantidad": "1.00",
                "precio_unitario": "1000.00",
                "subtotal": "1000.00",
            },
            format="json",
        )
        assert item_a.status_code == status.HTTP_201_CREATED

        item_b = api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": doc_b.data["id"],
                "producto": str(producto_b.id),
                "cantidad": "2.00",
                "precio_unitario": "2000.00",
                "subtotal": "4000.00",
            },
            format="json",
        )
        assert item_b.status_code == status.HTTP_201_CREATED

        listado = api_client.get(f"{reverse('documento-compra-item-list')}?documento={doc_a.data['id']}")
        assert listado.status_code == status.HTTP_200_OK
        payload = listado.data if isinstance(listado.data, list) else listado.data.get("results", [])
        assert len(payload) == 1
        assert str(payload[0]["id"]) == str(item_a.data["id"])

    def test_create_documento_siempre_queda_en_borrador(self, api_client, owner_usuario, proveedor):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        documento_resp = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "folio": "FAC-STATE-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
                "estado": "CONFIRMADO",
            },
            format="json",
        )
        assert documento_resp.status_code == status.HTTP_201_CREATED, documento_resp.data
        assert documento_resp.data["estado"] == "BORRADOR"

    def test_confirmacion_documentos_respeta_saldo_oc(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Match OC",
            sku="PMO-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {
                "proveedor": str(proveedor.id),
                "fecha_emision": str(date.today()),
            },
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED, orden_resp.data
        orden_id = orden_resp.data["id"]

        orden_item_resp = api_client.post(
            reverse("orden-compra-item-list"),
            {
                "orden_compra": orden_id,
                "producto": str(producto.id),
                "descripcion": "item match",
                "cantidad": "5.00",
                "precio_unitario": "1000.00",
            },
            format="json",
        )
        assert orden_item_resp.status_code == status.HTTP_201_CREATED, orden_item_resp.data

        doc_1 = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "orden_compra": str(orden_id),
                "folio": "FAC-M1",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
            },
            format="json",
        )
        assert doc_1.status_code == status.HTTP_201_CREATED, doc_1.data

        api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": doc_1.data["id"],
                "producto": str(producto.id),
                "cantidad": "3.00",
                "precio_unitario": "1000.00",
            },
            format="json",
        )

        conf_1 = api_client.post(reverse("documento-compra-confirmar-factura", args=[doc_1.data["id"]]), {}, format="json")
        assert conf_1.status_code == status.HTTP_200_OK, conf_1.data

        doc_2 = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "FACTURA_COMPRA",
                "proveedor": str(proveedor.id),
                "orden_compra": str(orden_id),
                "folio": "FAC-M2",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
            },
            format="json",
        )
        assert doc_2.status_code == status.HTTP_201_CREATED, doc_2.data

        api_client.post(
            reverse("documento-compra-item-list"),
            {
                "documento": doc_2.data["id"],
                "producto": str(producto.id),
                "cantidad": "3.00",
                "precio_unitario": "1000.00",
            },
            format="json",
        )

        conf_2 = api_client.post(reverse("documento-compra-confirmar-factura", args=[doc_2.data["id"]]), {}, format="json")
        assert conf_2.status_code == status.HTTP_409_CONFLICT

    def test_recepcion_compra_endpoint_confirma_y_actualiza_oc(self, api_client, owner_usuario, proveedor, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Recepcion API",
            sku="PR-API-01",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("500"),
        )

        orden_resp = api_client.post(
            reverse("orden-compra-list"),
            {
                "proveedor": str(proveedor.id),
                "fecha_emision": str(date.today()),
            },
            format="json",
        )
        assert orden_resp.status_code == status.HTTP_201_CREATED, orden_resp.data

        orden_id = orden_resp.data["id"]
        item_oc = api_client.post(
            reverse("orden-compra-item-list"),
            {
                "orden_compra": orden_id,
                "producto": str(producto.id),
                "descripcion": "Item recepcion",
                "cantidad": "2.00",
                "precio_unitario": "500.00",
            },
            format="json",
        )
        assert item_oc.status_code == status.HTTP_201_CREATED, item_oc.data

        documento = api_client.post(
            reverse("documento-compra-list"),
            {
                "tipo_documento": "GUIA_RECEPCION",
                "proveedor": str(proveedor.id),
                "orden_compra": orden_id,
                "folio": "GR-RECEP-API-001",
                "fecha_emision": str(date.today()),
                "fecha_recepcion": str(date.today()),
            },
            format="json",
        )
        assert documento.status_code == status.HTTP_201_CREATED, documento.data

        recepcion = api_client.post(
            reverse("recepcion-compra-list"),
            {
                "orden_compra": orden_id,
                "fecha": str(date.today()),
            },
            format="json",
        )
        assert recepcion.status_code == status.HTTP_201_CREATED, recepcion.data

        recepcion_item = api_client.post(
            reverse("recepcion-compra-item-list"),
            {
                "recepcion": recepcion.data["id"],
                "orden_item": item_oc.data["id"],
                "producto": str(producto.id),
                "cantidad": "2.00",
                "precio_unitario": "500.00",
            },
            format="json",
        )
        assert recepcion_item.status_code == status.HTTP_201_CREATED, recepcion_item.data

        confirmar = api_client.post(
            reverse("recepcion-compra-confirmar", args=[recepcion.data["id"]]),
            {},
            format="json",
        )
        assert confirmar.status_code == status.HTTP_200_OK, confirmar.data

        orden_actualizada = OrdenCompra.all_objects.get(id=orden_id)
        assert orden_actualizada.estado == "RECIBIDA"
