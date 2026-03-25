from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.models import AuditEvent
from apps.core.models import UserEmpresa
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import Bodega, MovimientoInventario, ReservaStock, StockProducto
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
    def test_bodegas_api_crea_normalizando_nombre(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        response = api_client.post(
            reverse("bodega-list"),
            {"nombre": "  casa   matriz  ", "activa": True},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["nombre"] == "CASA MATRIZ"
        assert response.data["activa"] is True

    def test_bodegas_api_actualiza_nombre_y_estado(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        bodega = Bodega.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Sucursal Norte",
            activa=True,
        )

        response = api_client.patch(
            reverse("bodega-detail", args=[bodega.id]),
            {"nombre": "  sucursal centro  ", "activa": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["nombre"] == "SUCURSAL CENTRO"
        assert response.data["activa"] is False

    def test_bodegas_api_elimina_bodega_sin_uso(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        bodega = Bodega.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Temporal",
            activa=True,
        )

        response = api_client.delete(reverse("bodega-detail", args=[bodega.id]))

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        assert not Bodega.all_objects.filter(id=bodega.id, empresa=empresa).exists()

    def test_bodegas_api_inactiva_bodega_con_uso_historico(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Bodega Historica",
            sku="PBH-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega = Bodega.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Historica",
            activa=True,
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            referencia="BODEGA-HISTORICA",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.delete(reverse("bodega-detail", args=[bodega.id]))

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["deleted"] is False
        assert response.data["bodega"]["activa"] is False

        bodega.refresh_from_db()
        assert bodega.activa is False

    def test_bodegas_api_lista_expone_flag_de_uso_historico(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Uso Bodega",
            sku="PUB-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega_historica = Bodega.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Historica Flag",
            activa=True,
        )
        bodega_limpia = Bodega.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Limpia Flag",
            activa=True,
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_historica.id,
            tipo="ENTRADA",
            cantidad=Decimal("1.00"),
            referencia="FLAG-HISTORICO",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.get(reverse("bodega-list"))

        assert response.status_code == status.HTTP_200_OK, response.data
        rows = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
        historial_por_id = {str(item["id"]): item["tiene_uso_historico"] for item in rows}
        assert historial_por_id[str(bodega_historica.id)] is True
        assert historial_por_id[str(bodega_limpia.id)] is False

    def test_ajuste_masivo_api_confirma_documento_con_varias_lineas(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        producto_a = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Ajuste Masivo A",
            sku="PAMA-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        producto_b = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Ajuste Masivo B",
            sku="PAMB-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Masiva Ajuste")

        response = api_client.post(
            reverse("ajuste-inventario-masivo-list"),
            {
                "referencia": "CONTEO GENERAL MARZO",
                "motivo": "CONTEO CICLICO",
                "observaciones": "Cierre parcial de pasillo",
                "items": [
                    {"producto_id": str(producto_a.id), "bodega_id": str(bodega.id), "stock_objetivo": "5.00"},
                    {"producto_id": str(producto_b.id), "bodega_id": str(bodega.id), "stock_objetivo": "3.00"},
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["estado"] == "CONFIRMADO"
        assert len(response.data["items"]) == 2
        movimientos = MovimientoInventario.all_objects.filter(
            empresa=empresa,
            documento_tipo=TipoDocumentoReferencia.AJUSTE,
            documento_id=response.data["id"],
        )
        assert movimientos.count() == 2

    def test_ajuste_masivo_api_filtra_y_duplica_documentos(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Ajuste Dup",
            sku="PAD-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Filtro Ajuste")
        create_response = api_client.post(
            reverse("ajuste-inventario-masivo-list"),
            {
                "referencia": "CONTEO DUPLICABLE",
                "motivo": "CONTEO",
                "observaciones": "",
                "items": [{"producto_id": str(producto.id), "bodega_id": str(bodega.id), "stock_objetivo": "2.00"}],
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data

        list_response = api_client.get(
            reverse("ajuste-inventario-masivo-list"),
            {"estado": "CONFIRMADO", "q": "DUPLICABLE"},
        )
        assert list_response.status_code == status.HTTP_200_OK, list_response.data
        rows = list_response.data["results"] if isinstance(list_response.data, dict) else list_response.data
        assert len(rows) == 1
        assert rows[0]["referencia"] == "CONTEO DUPLICABLE"

        duplicate_response = api_client.post(
            reverse("ajuste-inventario-masivo-duplicar", args=[create_response.data["id"]]),
            {},
            format="json",
        )
        assert duplicate_response.status_code == status.HTTP_201_CREATED, duplicate_response.data
        assert duplicate_response.data["id"] != create_response.data["id"]
        assert "DUPLICADO" in duplicate_response.data["referencia"]

    def test_traslado_masivo_api_confirma_documento_con_varias_lineas(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        producto_a = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Traslado Masivo A",
            sku="PTMA-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        producto_b = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Traslado Masivo B",
            sku="PTMB-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Origen Masivo")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Destino Masivo")
        InventarioService.registrar_movimiento(
            producto_id=producto_a.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("6.00"),
            referencia="BASE-MASIVO-A",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.registrar_movimiento(
            producto_id=producto_b.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("4.00"),
            referencia="BASE-MASIVO-B",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.post(
            reverse("traslado-inventario-masivo-list"),
            {
                "referencia": "REUBICACION DE PASILLO",
                "motivo": "CAMBIO DE LAYOUT",
                "observaciones": "Reordenamiento semanal",
                "bodega_origen_id": str(bodega_origen.id),
                "bodega_destino_id": str(bodega_destino.id),
                "items": [
                    {"producto_id": str(producto_a.id), "cantidad": "2.00"},
                    {"producto_id": str(producto_b.id), "cantidad": "1.00"},
                ],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data["estado"] == "CONFIRMADO"
        assert len(response.data["items"]) == 2
        movimientos = MovimientoInventario.all_objects.filter(
            empresa=empresa,
            documento_tipo=TipoDocumentoReferencia.TRASLADO,
            documento_id=response.data["id"],
        )
        assert movimientos.count() == 4

    def test_traslado_masivo_api_filtra_y_duplica_documentos(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Traslado Dup",
            sku="PTD-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Origen Dup")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Destino Dup")
        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("6.00"),
            referencia="BASE-DUP",
            empresa=empresa,
            usuario=owner_usuario,
        )

        create_response = api_client.post(
            reverse("traslado-inventario-masivo-list"),
            {
                "referencia": "REUBICACION DUPLICABLE",
                "motivo": "LAYOUT",
                "observaciones": "",
                "bodega_origen_id": str(bodega_origen.id),
                "bodega_destino_id": str(bodega_destino.id),
                "items": [{"producto_id": str(producto.id), "cantidad": "2.00"}],
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data

        list_response = api_client.get(
            reverse("traslado-inventario-masivo-list"),
            {"estado": "CONFIRMADO", "q": "DUPLICABLE"},
        )
        assert list_response.status_code == status.HTTP_200_OK, list_response.data
        rows = list_response.data["results"] if isinstance(list_response.data, dict) else list_response.data
        assert len(rows) == 1
        assert rows[0]["referencia"] == "REUBICACION DUPLICABLE"

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("4.00"),
            referencia="BASE-DUP-2",
            empresa=empresa,
            usuario=owner_usuario,
        )
        duplicate_response = api_client.post(
            reverse("traslado-inventario-masivo-duplicar", args=[create_response.data["id"]]),
            {},
            format="json",
        )
        assert duplicate_response.status_code == status.HTTP_201_CREATED, duplicate_response.data
        assert duplicate_response.data["id"] != create_response.data["id"]
        assert "DUPLICADO" in duplicate_response.data["referencia"]

    def test_previsualizar_regularizacion_por_api_devuelve_diferencia(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Preview API",
            sku="PPREV-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        movimiento = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("10.00"),
            referencia="STOCK-PREVIEW",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.reservar_stock(
            producto_id=producto.id,
            bodega_id=movimiento.bodega_id,
            cantidad=Decimal("2.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="88888888-8888-8888-8888-888888888888",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.post(
            reverse("movimiento-inventario-previsualizar-regularizacion"),
            {
                "producto_id": str(producto.id),
                "bodega_id": str(movimiento.bodega_id),
                "stock_objetivo": "6.00",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["tipo_movimiento"] == "SALIDA"
        assert Decimal(str(resp.data["diferencia"])) == Decimal("-4.00")
        assert Decimal(str(resp.data["reservado_total"])) == Decimal("2.00")
        assert resp.data["ajustable"] is True

    def test_previsualizar_regularizacion_advierte_bajo_reservado(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Preview Reserva",
            sku="PPREV-002",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        movimiento = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("5.00"),
            referencia="STOCK-PREVIEW-RES",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.reservar_stock(
            producto_id=producto.id,
            bodega_id=movimiento.bodega_id,
            cantidad=Decimal("4.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="99999999-9999-9999-9999-999999999999",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.post(
            reverse("movimiento-inventario-previsualizar-regularizacion"),
            {
                "producto_id": str(producto.id),
                "bodega_id": str(movimiento.bodega_id),
                "stock_objetivo": "3.00",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["ajustable"] is False
        assert "reservado" in " ".join(resp.data["warnings"]).lower()

    def test_trasladar_stock_por_api_mueve_existencia_entre_bodegas(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Traslado API",
            sku="PTR-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Origen API")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Destino API")

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("6.00"),
            referencia="STOCK-ORIGEN",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.post(
            reverse("movimiento-inventario-trasladar"),
            {
                "producto_id": str(producto.id),
                "bodega_origen_id": str(bodega_origen.id),
                "bodega_destino_id": str(bodega_destino.id),
                "cantidad": "2.00",
                "referencia": "Traslado interno",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["movimiento_salida"]["documento_tipo"] == "TRASLADO"
        assert resp.data["movimiento_entrada"]["documento_tipo"] == "TRASLADO"

        stock_origen = StockProducto.all_objects.get(empresa=empresa, producto=producto, bodega=bodega_origen)
        stock_destino = StockProducto.all_objects.get(empresa=empresa, producto=producto, bodega=bodega_destino)
        producto.refresh_from_db()
        assert Decimal(stock_origen.stock) == Decimal("4.00")
        assert Decimal(stock_destino.stock) == Decimal("2.00")
        assert producto.stock_actual == Decimal("6.00")

    def test_trasladar_stock_rechaza_misma_bodega_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Traslado Invalido",
            sku="PTR-002",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Bodega API")

        resp = api_client.post(
            reverse("movimiento-inventario-trasladar"),
            {
                "producto_id": str(producto.id),
                "bodega_origen_id": str(bodega.id),
                "bodega_destino_id": str(bodega.id),
                "cantidad": "1.00",
                "referencia": "Traslado invalido",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert resp.data["error_code"] == "BUSINESS_RULE_ERROR"

    def test_regularizar_stock_por_api_crea_ajuste(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Regularizacion API",
            sku="PREG-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("8.00"),
            referencia="STOCK-INICIAL-REG",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.post(
            reverse("movimiento-inventario-regularizar"),
            {
                "producto_id": str(producto.id),
                "stock_objetivo": "5.00",
                "referencia": "Conteo fisico marzo",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert resp.data["tipo"] == "SALIDA"
        assert resp.data["documento_tipo"] == "AJUSTE"
        assert Decimal(str(resp.data["cantidad"])) == Decimal("3.00")

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("5.00")

    def test_regularizar_stock_rechaza_bajar_de_reservado(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Regularizacion Reserva",
            sku="PREG-002",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )

        movimiento = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("5.00"),
            referencia="ENTRADA-RESERVA-API",
            empresa=empresa,
            usuario=owner_usuario,
        )
        ReservaStock.all_objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            producto=producto,
            bodega_id=movimiento.bodega_id,
            cantidad=Decimal("4.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="66666666-6666-6666-6666-666666666666",
        )

        resp = api_client.post(
            reverse("movimiento-inventario-regularizar"),
            {
                "producto_id": str(producto.id),
                "bodega_id": str(movimiento.bodega_id),
                "stock_objetivo": "3.00",
                "referencia": "Conteo bajo reserva",
            },
            format="json",
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
        assert resp.data["error_code"] == "BUSINESS_RULE_ERROR"

    def test_resumen_incluye_reservado_y_disponible(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Resumen Reserva",
            sku="PRR-0001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("5.00"),
            referencia="RESERVA-RESUMEN",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.reservar_stock(
            producto_id=producto.id,
            cantidad=Decimal("2.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="44444444-4444-4444-4444-444444444444",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(reverse("stock-producto-resumen"), {"group_by": "producto"})

        assert resp.status_code == status.HTTP_200_OK
        assert Decimal(str(resp.data["totales"]["reservado_total"])) == Decimal("2")
        assert Decimal(str(resp.data["totales"]["disponible_total"])) == Decimal("3")

        row = next(item for item in resp.data["detalle"] if str(item["producto_id"]) == str(producto.id))
        assert Decimal(str(row["reservado_total"])) == Decimal("2")
        assert Decimal(str(row["disponible_total"])) == Decimal("3")

    def test_stocks_endpoint_rechaza_mutacion_directa_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Solo Lectura",
            sku="PSL-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Principal API ReadOnly")

        response = api_client.post(
            reverse("stock-producto-list"),
            {
                "producto": str(producto.id),
                "bodega": str(bodega.id),
                "stock": "99.00",
                "valor_stock": "1000.00",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
        assert response.data["error_code"] == "PERMISSION_DENIED"

    def test_regularizar_stock_producto_inexistente_retorna_404(self, api_client, owner_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        response = api_client.post(
            reverse("movimiento-inventario-regularizar"),
            {
                "producto_id": "11111111-1111-1111-1111-111111111111",
                "stock_objetivo": "5.00",
                "referencia": "Conteo producto inexistente",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, response.data
        assert response.data["error_code"] == "RESOURCE_NOT_FOUND"

    def test_previsualizar_regularizacion_producto_inexistente_retorna_404(self, api_client, owner_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        response = api_client.post(
            reverse("movimiento-inventario-previsualizar-regularizacion"),
            {
                "producto_id": "11111111-1111-1111-1111-111111111111",
                "stock_objetivo": "5.00",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND, response.data
        assert response.data["error_code"] == "RESOURCE_NOT_FOUND"

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

    def test_movimiento_auditoria_detalle_retorna_eventos_con_changes(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Auditoria Detalle",
            sku="PAUD-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("2000"),
        )

        movimiento = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("3.00"),
            costo_unitario=Decimal("1500.00"),
            referencia="AUDITORIA-DETALLE",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.get(reverse("movimiento-inventario-auditoria", args=[movimiento.id]))

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] >= 1
        evento = response.data["results"][0]
        assert evento["entity_type"] == "MOVIMIENTO_INVENTARIO"
        assert evento["entity_id"] == str(movimiento.id)
        assert evento["changes"]["stock_bodega"] == ["0.00", "3.00"]
        assert evento["changes"]["stock_global_producto"] == ["0.00", "3.00"]

    def test_movimiento_historial_filtra_por_producto(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto_a = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Historial A",
            sku="PHA-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )
        producto_b = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Historial B",
            sku="PHB-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        movimiento_a = InventarioService.registrar_movimiento(
            producto_id=producto_a.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            referencia="HIST-A",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.registrar_movimiento(
            producto_id=producto_b.id,
            tipo="ENTRADA",
            cantidad=Decimal("4.00"),
            referencia="HIST-B",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.get(
            reverse("movimiento-inventario-historial"),
            {"producto_id": str(producto_a.id)},
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 1
        assert response.data["results"][0]["entity_id"] == str(movimiento_a.id)

    def test_movimiento_historial_filtra_por_referencia(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Historial Ref",
            sku="PHR-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        movimiento_match = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            referencia="CONTEO MARZO CASA MATRIZ",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("1.00"),
            referencia="CONTEO ABRIL SUCURSAL",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.get(
            reverse("movimiento-inventario-historial"),
            {"referencia": "marzo"},
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 1
        assert response.data["results"][0]["entity_id"] == str(movimiento_match.id)

    def test_movimiento_auditoria_traslado_consolida_ambas_piernas(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Traslado Auditoria",
            sku="PTA-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Origen Aud")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Destino Aud")

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("6.00"),
            referencia="BASE-TRAS-AUD",
            empresa=empresa,
            usuario=owner_usuario,
        )
        traslado = InventarioService.trasladar_stock(
            producto_id=producto.id,
            bodega_origen_id=bodega_origen.id,
            bodega_destino_id=bodega_destino.id,
            cantidad=Decimal("2.00"),
            referencia="TRASLADO-AUDITORIA",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.get(
            reverse("movimiento-inventario-auditoria", args=[traslado["movimiento_salida"].id])
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        entity_ids = {item["entity_id"] for item in response.data["results"]}
        assert str(traslado["movimiento_salida"].id) in entity_ids
        assert str(traslado["movimiento_entrada"].id) in entity_ids
        assert AuditEvent.all_objects.filter(
            empresa=empresa,
            entity_type="MOVIMIENTO_INVENTARIO",
            entity_id=str(traslado["movimiento_salida"].id),
        ).exists()

    def test_movimiento_historial_traslado_expone_bodegas_relacionadas(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Historial Traslado",
            sku="PHT-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Origen Hist")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Destino Hist")

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("6.00"),
            referencia="BASE-TRAS-HIST",
            empresa=empresa,
            usuario=owner_usuario,
        )
        traslado = InventarioService.trasladar_stock(
            producto_id=producto.id,
            bodega_origen_id=bodega_origen.id,
            bodega_destino_id=bodega_destino.id,
            cantidad=Decimal("2.00"),
            referencia="TRASLADO-HISTORIAL",
            empresa=empresa,
            usuario=owner_usuario,
        )

        response = api_client.get(
            reverse("movimiento-inventario-historial"),
            {"documento_tipo": "TRASLADO", "documento_id": traslado["traslado_id"]},
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["count"] == 2
        payloads = [item["payload"] for item in response.data["results"]]
        assert all(payload["bodega_origen_id"] == str(bodega_origen.id) for payload in payloads)
        assert all(payload["bodega_destino_id"] == str(bodega_destino.id) for payload in payloads)

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

    def test_kardex_compra_recepcion_incluye_factura_compra(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Kardex Compra Familia",
            sku="PK-COMPRA-1",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1800"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("2.00"),
            referencia="COMPRA RECEPCION",
            empresa=empresa,
            usuario=owner_usuario,
            documento_tipo=TipoDocumentoReferencia.COMPRA_RECEPCION,
        )
        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("1.00"),
            referencia="COMPRA FACTURA",
            empresa=empresa,
            usuario=owner_usuario,
            documento_tipo=TipoDocumentoReferencia.FACTURA_COMPRA,
        )

        resp = api_client.get(
            reverse("movimiento-inventario-kardex"),
            {
                "producto_id": str(producto.id),
                "documento_tipo": "COMPRA_RECEPCION",
            },
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 2

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

    def test_criticos_endpoint_devuelve_productos_bajo_stock_minimo(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto_critico = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Critico",
            sku="PCRIT-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            stock_minimo=Decimal("5.00"),
            precio_referencia=Decimal("2500"),
        )
        producto_sano = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Sano",
            sku="PSANO-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            stock_minimo=Decimal("2.00"),
            precio_referencia=Decimal("2500"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto_critico.id,
            tipo="ENTRADA",
            cantidad=Decimal("3.00"),
            referencia="CRITICO-TEST",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.registrar_movimiento(
            producto_id=producto_sano.id,
            tipo="ENTRADA",
            cantidad=Decimal("4.00"),
            referencia="SANO-TEST",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(reverse("stock-producto-criticos"))

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert str(resp.data["detalle"][0]["producto_id"]) == str(producto_critico.id)
        assert Decimal(str(resp.data["detalle"][0]["faltante"])) == Decimal("2")

    def test_criticos_endpoint_exige_permiso_ver(self, api_client, empresa):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="sin_permiso_criticos",
            email="sin_permiso_criticos@test.com",
            password="pass1234",
            empresa_activa=empresa,
        )
        UserEmpresa.objects.create(user=user, empresa=empresa, rol="BODEGA", activo=True)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(user)}")
        resp = api_client.get(reverse("stock-producto-criticos"))

        assert resp.status_code == status.HTTP_403_FORBIDDEN, resp.data
        assert resp.data["error_code"] == "PERMISSION_DENIED"

    def test_analytics_inventario_retorna_metricas_y_top(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        categoria = Categoria.objects.create(
            empresa=empresa,
            nombre="Farmacia",
            descripcion="Categoria test analytics",
            activa=True,
        )
        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Vacuna canina",
            sku="VAC-001",
            categoria=categoria,
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            stock_minimo=Decimal("5.00"),
            precio_referencia=Decimal("2500"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("3.00"),
            costo_unitario=Decimal("1000.00"),
            referencia="ANALYTICS-INV",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(
            reverse("stock-producto-analytics"),
            {"group_by": "producto", "only_with_stock": "true"},
        )

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["filters"]["group_by"] == "producto"
        assert resp.data["filters"]["only_with_stock"] is True
        assert resp.data["metrics"]["registros"] == 1
        assert len(resp.data["top_valorizados"]) == 1
        assert resp.data["top_valorizados"][0]["producto__nombre"] == "VACUNA CANINA"
        assert len(resp.data["criticos"]) == 1
        assert resp.data["criticos"][0]["producto__nombre"] == "VACUNA CANINA"
        assert Decimal(str(resp.data["metrics"]["valor_total"])) == Decimal("3000")

    def test_resumen_operativo_movimientos_retorna_metricas(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        producto = Producto.objects.create(
            empresa=empresa,
            nombre="Producto Resumen Mov",
            sku="PRM-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1500"),
        )
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Origen Resumen")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=owner_usuario, nombre="Destino Resumen")

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            tipo="ENTRADA",
            cantidad=Decimal("10.00"),
            referencia="ENTRADA-RESUMEN",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.regularizar_stock(
            producto_id=producto.id,
            bodega_id=bodega_origen.id,
            stock_objetivo=Decimal("8.00"),
            referencia="AJUSTE-RESUMEN",
            empresa=empresa,
            usuario=owner_usuario,
        )
        InventarioService.trasladar_stock(
            producto_id=producto.id,
            bodega_origen_id=bodega_origen.id,
            bodega_destino_id=bodega_destino.id,
            cantidad=Decimal("3.00"),
            referencia="TRASLADO-RESUMEN",
            empresa=empresa,
            usuario=owner_usuario,
        )

        resp = api_client.get(reverse("movimiento-inventario-resumen-operativo"))

        assert resp.status_code == status.HTTP_200_OK, resp.data
        assert resp.data["total_movimientos"] == 4
        assert resp.data["entradas"] == 2
        assert resp.data["salidas"] == 2
        assert resp.data["ajustes"] == 1
        assert resp.data["traslados"] == 2
        assert Decimal(str(resp.data["cantidad_entrada"])) == Decimal("13.00")
        assert Decimal(str(resp.data["cantidad_salida"])) == Decimal("5.00")
        assert Decimal(str(resp.data["neto_unidades"])) == Decimal("8.00")

    def test_resumen_operativo_movimientos_exige_permiso_ver(self, api_client, empresa):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="sin_permiso_resumen_mov",
            email="sin_permiso_resumen_mov@test.com",
            password="pass1234",
            empresa_activa=empresa,
        )
        UserEmpresa.objects.create(user=user, empresa=empresa, rol="BODEGA", activo=True)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(user)}")
        resp = api_client.get(reverse("movimiento-inventario-resumen-operativo"))

        assert resp.status_code == status.HTTP_403_FORBIDDEN, resp.data
        assert resp.data["error_code"] == "PERMISSION_DENIED"
