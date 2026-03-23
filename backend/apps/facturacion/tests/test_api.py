from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa


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
class TestFacturacionApi:
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

    def test_preview_rangos_folios_no_persiste_cambios(self, api_client, owner_usuario, empresa):
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
        sheet.append(["FACTURA_VENTA", "CAF PREVIEW", 200, 250, 205, "2026-01-01", "2026-12-31", True])

        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "rangos_preview.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = api_client.post(
            reverse("rango-folio-tributario-bulk-import"),
            {"file": upload, "dry_run": "true"},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["dry_run"] is True
        assert response.data["created"] == 1
        list_resp = api_client.get(reverse("rango-folio-tributario-list"))
        assert list_resp.status_code == status.HTTP_200_OK, list_resp.data
        assert len(list_resp.data) == 0

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
