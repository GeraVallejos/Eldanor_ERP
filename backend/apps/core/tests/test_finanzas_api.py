from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contactos.models import Cliente, Contacto
from apps.core.models import Moneda, UserEmpresa


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_finanzas_api",
        email="owner_finanzas_api@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestFinanzasApi:
    def test_importar_rangos_folios_desde_xlsx(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        api_client.post(
            reverse("configuracion-tributaria-list"),
            {
                "ambiente": "CERTIFICACION",
                "rut_emisor": "76086428-5",
                "razon_social": "Empresa Test SII",
                "certificado_alias": "cert-prueba",
                "certificado_activo": True,
                "resolucion_numero": 80,
                "resolucion_fecha": "2026-01-01",
                "email_intercambio_dte": "dte@test.com",
                "proveedor_envio": "INTERNO",
                "activa": True,
            },
            format="json",
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            "tipo_documento",
            "caf_nombre",
            "folio_desde",
            "folio_hasta",
            "folio_actual",
            "fecha_autorizacion",
            "fecha_vencimiento",
            "activo",
        ])
        sheet.append(["FACTURA_VENTA", "CAF FACTURAS", 100, 150, 120, "2026-01-01", "2026-12-31", True])

        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "rangos_sii.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = api_client.post(
            reverse("rango-folio-tributario-bulk-import"),
            {"file": upload},
            format="multipart",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["created"] == 1

    def test_configuracion_tributaria_y_rango_folio_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        config_resp = api_client.post(
            reverse("configuracion-tributaria-list"),
            {
                "ambiente": "CERTIFICACION",
                "rut_emisor": "76086428-5",
                "razon_social": "Empresa Test SII",
                "certificado_alias": "cert-prueba",
                "certificado_activo": True,
                "resolucion_numero": 80,
                "resolucion_fecha": "2026-01-01",
                "email_intercambio_dte": "dte@test.com",
                "proveedor_envio": "INTERNO",
                "activa": True,
            },
            format="json",
        )
        assert config_resp.status_code == status.HTTP_201_CREATED, config_resp.data

        rango_resp = api_client.post(
            reverse("rango-folio-tributario-list"),
            {
                "tipo_documento": "FACTURA_VENTA",
                "caf_nombre": "CAF FACTURAS 2026",
                "folio_desde": 100,
                "folio_hasta": 150,
                "fecha_autorizacion": "2026-01-01",
                "fecha_vencimiento": "2026-12-31",
                "activo": True,
            },
            format="json",
        )
        assert rango_resp.status_code == status.HTTP_201_CREATED, rango_resp.data

        list_resp = api_client.get(reverse("rango-folio-tributario-list"))
        assert list_resp.status_code == status.HTTP_200_OK, list_resp.data
        assert len(list_resp.data) == 1

    def test_tipos_cambio_convertir_endpoint(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        usd = Moneda.all_objects.get(empresa=empresa, codigo="USD")
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        create_resp = api_client.post(
            reverse("tipo-cambio-list"),
            {
                "moneda_origen": str(usd.id),
                "moneda_destino": str(clp.id),
                "fecha": "2026-03-12",
                "tasa": "950",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data

        convert_resp = api_client.post(
            reverse("tipo-cambio-convertir"),
            {
                "monto": "10",
                "moneda_origen": "USD",
                "moneda_destino": "CLP",
                "fecha": "2026-03-12",
            },
            format="json",
        )
        assert convert_resp.status_code == status.HTTP_200_OK, convert_resp.data
        assert Decimal(str(convert_resp.data["monto_convertido"])) == Decimal("9500")

    def test_cuentas_por_cobrar_crear_y_aplicar_pago(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente API Finanzas",
            rut="12312312-3",
            email="cliente_finanzas_api@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        create_resp = api_client.post(
            reverse("cuenta-por-cobrar-list"),
            {
                "cliente": str(cliente.id),
                "moneda": str(clp.id),
                "referencia": "CXC-API-001",
                "fecha_emision": "2026-03-12",
                "fecha_vencimiento": "2026-03-30",
                "monto_total": "100000",
                "saldo": "100000",
                "estado": "PENDIENTE",
            },
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED, create_resp.data

        pago_resp = api_client.post(
            reverse("cuenta-por-cobrar-aplicar-pago", args=[create_resp.data["id"]]),
            {
                "monto": "25000",
                "fecha_pago": "2026-03-15",
            },
            format="json",
        )
        assert pago_resp.status_code == status.HTTP_200_OK, pago_resp.data
        assert Decimal(str(pago_resp.data["saldo"])) == Decimal("75000")
        assert pago_resp.data["estado"] == "PARCIAL"

    def test_movimiento_bancario_crear_y_conciliar_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Conciliacion API",
            rut="12312312-3",
            email="cliente_conciliacion_api@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        cuenta_resp = api_client.post(
            reverse("cuenta-bancaria-list"),
            {
                "alias": "Banco Principal",
                "banco": "Banco Estado",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "123456789",
                "titular": "Empresa Test",
                "moneda": str(clp.id),
                "saldo_referencial": "0",
                "activa": True,
            },
            format="json",
        )
        assert cuenta_resp.status_code == status.HTTP_201_CREATED, cuenta_resp.data

        cxc_resp = api_client.post(
            reverse("cuenta-por-cobrar-list"),
            {
                "cliente": str(cliente.id),
                "moneda": str(clp.id),
                "referencia": "CXC-API-BANCO-001",
                "fecha_emision": "2026-03-12",
                "fecha_vencimiento": "2026-03-30",
                "monto_total": "100000",
                "saldo": "100000",
                "estado": "PENDIENTE",
            },
            format="json",
        )
        assert cxc_resp.status_code == status.HTTP_201_CREATED, cxc_resp.data

        movimiento_resp = api_client.post(
            reverse("movimiento-bancario-list"),
            {
                "cuenta_bancaria": str(cuenta_resp.data["id"]),
                "fecha": "2026-03-15",
                "referencia": "DEP-001",
                "descripcion": "Deposito cliente",
                "tipo": "CREDITO",
                "monto": "100000",
            },
            format="json",
        )
        assert movimiento_resp.status_code == status.HTTP_201_CREATED, movimiento_resp.data

        conciliar_resp = api_client.post(
            reverse("movimiento-bancario-conciliar", args=[movimiento_resp.data["id"]]),
            {"cuenta_por_cobrar": cxc_resp.data["id"]},
            format="json",
        )
        assert conciliar_resp.status_code == status.HTTP_200_OK, conciliar_resp.data
        assert conciliar_resp.data["conciliado"] is True
        assert str(conciliar_resp.data["cuenta_por_cobrar"]) == cxc_resp.data["id"]

        detalle_cxc = api_client.get(reverse("cuenta-por-cobrar-detail", args=[cxc_resp.data["id"]]))
        assert detalle_cxc.status_code == status.HTTP_200_OK, detalle_cxc.data
        assert Decimal(str(detalle_cxc.data["saldo"])) == Decimal("0")
        assert detalle_cxc.data["estado"] == "PAGADA"

    def test_importar_movimientos_bancarios_desde_xlsx(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        cuenta_resp = api_client.post(
            reverse("cuenta-bancaria-list"),
            {
                "alias": "Banco Principal",
                "banco": "Banco Estado",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "123456789",
                "titular": "Empresa Test",
                "moneda": str(clp.id),
                "saldo_referencial": "0",
                "activa": True,
            },
            format="json",
        )
        assert cuenta_resp.status_code == status.HTTP_201_CREATED, cuenta_resp.data

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["numero_cuenta", "alias_cuenta", "fecha", "tipo", "monto", "referencia", "descripcion"])
        sheet.append(["123456789", "Banco Principal", "2026-03-20", "CREDITO", "75500", "DEP-002", "Pago cliente"])

        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "movimientos_bancos.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = api_client.post(
            reverse("movimiento-bancario-bulk-import"),
            {"file": upload},
            format="multipart",
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["created"] == 1

        listado = api_client.get(reverse("movimiento-bancario-list"))
        assert listado.status_code == status.HTTP_200_OK, listado.data
        assert len(listado.data) == 1
