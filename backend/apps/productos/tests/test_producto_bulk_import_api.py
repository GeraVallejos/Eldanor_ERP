from decimal import Decimal
import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.productos.models import Producto


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def admin_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_bulk_productos",
        email="admin_bulk_productos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)
    return user


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_bulk_productos",
        email="owner_bulk_productos@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestProductoBulkImportApi:
    def test_admin_puede_cargar_productos_por_csv(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        csv_content = "\n".join([
            "nombre,sku,tipo,precio_referencia,precio_costo,maneja_inventario,activo",
            "Producto Uno,SKU-001,PRODUCTO,1200,800,true,true",
            "Servicio Dos,SKU-002,SERVICIO,2500,0,false,true",
        ])

        file = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(reverse("producto-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 2
        assert response.data["updated"] == 0
        assert response.data["errors"] == []

        producto = Producto.all_objects.get(empresa=empresa, sku="SKU-001")
        servicio = Producto.all_objects.get(empresa=empresa, sku="SKU-002")
        assert producto.nombre == "PRODUCTO UNO"
        assert producto.precio_referencia == Decimal("1200")
        assert producto.stock_actual == Decimal("0")
        assert producto.costo_promedio == Decimal("800")
        assert servicio.maneja_inventario is False
        assert servicio.stock_actual == Decimal("0")
        assert servicio.costo_promedio == Decimal("0")

    def test_owner_no_puede_carga_masiva_por_regla_admin_only(self, api_client, owner_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        csv_content = "nombre,sku\nProducto Tres,SKU-003\n"
        file = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(reverse("producto-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error_code"] == "BULK_IMPORT_ADMIN_ONLY"

    def test_admin_puede_cargar_productos_por_xlsx(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["nombre", "sku", "tipo", "precio_referencia", "activo"])
        sheet.append(["Producto XLSX", "SKU-XLSX-01", "PRODUCTO", 999, True])

        buffer = io.BytesIO()
        workbook.save(buffer)
        file = SimpleUploadedFile(
            "productos.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = api_client.post(reverse("producto-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 1
        assert response.data["errors"] == []

        producto = Producto.all_objects.get(empresa=empresa, sku="SKU-XLSX-01")
        assert producto.nombre == "PRODUCTO XLSX"

    def test_admin_puede_descargar_plantilla_xlsx(self, api_client, admin_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        response = api_client.get(reverse("producto-bulk-template"))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "attachment; filename=\"plantilla_productos.xlsx\"" in response["Content-Disposition"]

    def test_admin_no_puede_importar_csv_legacy_con_stock_actual(self, api_client, admin_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        csv_content = "\n".join([
            "nombre,sku,stock_actual",
            "Producto Legacy,SKU-LEGACY-002,5",
        ])

        file = SimpleUploadedFile("productos.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(reverse("producto-bulk-import"), {"file": file}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error_code"] == "BULK_IMPORT_STOCK_ACTUAL_NO_SOPORTADO"
