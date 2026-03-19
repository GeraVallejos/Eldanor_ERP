import pytest
import io
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.contactos.models import Cliente, Contacto, Proveedor
from apps.core.models import UserEmpresa


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def admin_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_bulk_contactos",
        email="admin_bulk_contactos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)
    return user


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_bulk_contactos",
        email="owner_bulk_contactos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestContactosBulkImportApi:
    def test_admin_puede_importar_clientes(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        csv_content = "\n".join([
            "nombre,rut,email,tipo,limite_credito,dias_credito,categoria_cliente,segmento,activo",
            "Cliente Uno,11111111-1,cliente1@test.com,EMPRESA,500000,30,ORO,RETAIL,true",
            "Cliente Dos,22222222-2,cliente2@test.com,PERSONA,0,0,,SERVICIOS,true",
        ])
        file = SimpleUploadedFile("clientes.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(reverse("cliente-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 2
        assert response.data["updated"] == 0
        assert response.data["errors"] == []

        assert Cliente.all_objects.filter(empresa=empresa).count() == 2
        assert Contacto.all_objects.filter(empresa=empresa).count() == 2

    def test_admin_puede_importar_proveedores(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        csv_content = "\n".join([
            "nombre,rut,email,tipo,giro,vendedor_contacto,dias_credito,activo",
            "Proveedor Uno,33333333-3,prov1@test.com,EMPRESA,Construccion,Ana,15,true",
        ])
        file = SimpleUploadedFile("proveedores.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(reverse("proveedor-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 1
        assert response.data["updated"] == 0
        assert response.data["errors"] == []

        assert Proveedor.all_objects.filter(empresa=empresa).count() == 1

    def test_owner_no_puede_carga_masiva_contactos(self, api_client, owner_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        csv_content = "nombre\nCliente Owner\n"
        file = SimpleUploadedFile("clientes.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(reverse("cliente-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error_code"] == "BULK_IMPORT_ADMIN_ONLY"

    def test_admin_puede_importar_clientes_desde_xlsx(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["nombre", "rut", "email", "tipo", "limite_credito", "dias_credito", "activo"])
        sheet.append(["Cliente XLSX", "44444444-4", "cliente_xlsx@test.com", "EMPRESA", 120000, 10, True])

        buffer = io.BytesIO()
        workbook.save(buffer)
        file = SimpleUploadedFile(
            "clientes.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = api_client.post(reverse("cliente-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 1
        assert response.data["errors"] == []
        assert Cliente.all_objects.filter(empresa=empresa).count() == 1

    def test_import_rechaza_rut_con_dv_invalido(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        csv_content = "\n".join([
            "nombre,rut,email,tipo,activo",
            "Cliente DV Malo,12345678-9,cliente_dv@test.com,EMPRESA,true",
        ])
        file = SimpleUploadedFile("clientes.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = api_client.post(reverse("cliente-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 0
        assert len(response.data["errors"]) == 1
        assert "digito verificador" in response.data["errors"][0]["detail"].lower()
        assert Cliente.all_objects.filter(empresa=empresa).count() == 0

    def test_import_guarda_rut_formateado_chileno(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        csv_content = "\n".join([
            "nombre,rut,email,tipo,activo",
            "Cliente Formato,123456785,cliente_formato@test.com,EMPRESA,true",
        ])
        file = SimpleUploadedFile("clientes.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = api_client.post(reverse("cliente-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 1
        assert response.data["errors"] == []
        contacto = Contacto.all_objects.get(empresa=empresa, email="cliente_formato@test.com")
        assert contacto.rut == "12.345.678-5"

    def test_admin_puede_descargar_plantilla_xlsx_clientes(self, api_client, admin_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        response = api_client.get(reverse("cliente-bulk-template"))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "attachment; filename=\"plantilla_clientes.xlsx\"" in response["Content-Disposition"]


