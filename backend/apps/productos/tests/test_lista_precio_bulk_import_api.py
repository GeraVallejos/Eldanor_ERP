from datetime import date
import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import UserEmpresa
from apps.productos.models import ListaPrecio, ListaPrecioItem, Producto
from apps.tesoreria.models import Moneda


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def admin_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="admin_bulk_lista_precio",
        email="admin_bulk_lista_precio@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)
    return user


@pytest.fixture
def owner_usuario(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_bulk_lista_precio",
        email="owner_bulk_lista_precio@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestListaPrecioBulkImportApi:
    def test_admin_puede_importar_items_sobre_lista_existente(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Lista API Bulk",
            moneda=moneda,
            fecha_desde=date(2026, 1, 1),
            activa=True,
            prioridad=100,
        )
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Producto API Bulk",
            sku="SKU-LISTA-API-001",
            precio_referencia="12000",
        )

        csv_content = "\n".join([
            "sku,precio,descuento_maximo",
            "SKU-LISTA-API-001,10990,6",
        ])
        file = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = api_client.post(
            reverse("lista-precio-bulk-import", args=[lista.id]),
            {"file": file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["created"] == 1
        assert response.data["updated"] == 0
        assert response.data["errors"] == []

        item = ListaPrecioItem.all_objects.get(empresa=empresa, lista=lista, producto=producto)
        assert str(item.precio) in {"10990", "10990.00"}
        assert str(item.descuento_maximo) in {"6", "6.00"}

    def test_owner_no_puede_importar_items_por_regla_admin_only(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Lista API Owner",
            moneda=moneda,
            fecha_desde=date(2026, 1, 1),
            activa=True,
            prioridad=50,
        )

        csv_content = "sku,precio\nSKU-001,9990\n"
        file = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = api_client.post(
            reverse("lista-precio-bulk-import", args=[lista.id]),
            {"file": file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error_code"] == "BULK_IMPORT_ADMIN_ONLY"

    def test_admin_puede_descargar_plantilla_de_lista(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Lista Plantilla",
            moneda=moneda,
            fecha_desde=date(2026, 1, 1),
            activa=True,
            prioridad=10,
        )

        response = api_client.get(reverse("lista-precio-bulk-template", args=[lista.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "attachment; filename=" in response["Content-Disposition"]

    def test_admin_puede_importar_xlsx_de_lista(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Lista XLSX",
            moneda=moneda,
            fecha_desde=date(2026, 1, 1),
            activa=True,
            prioridad=200,
        )
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Producto XLSX Lista",
            sku="SKU-LISTA-XLSX-01",
            precio_referencia="8800",
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["sku", "precio", "descuento_maximo"])
        sheet.append([producto.sku, 8450, 2])

        buffer = io.BytesIO()
        workbook.save(buffer)
        file = SimpleUploadedFile(
            "lista_precios.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        response = api_client.post(
            reverse("lista-precio-bulk-import", args=[lista.id]),
            {"file": file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 1
        assert response.data["errors"] == []

    def test_admin_puede_previsualizar_importacion_sin_persistir(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Lista Preview API",
            moneda=moneda,
            fecha_desde=date(2026, 1, 1),
            activa=True,
            prioridad=100,
        )
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Producto Preview API",
            sku="SKU-LISTA-PREVIEW-API-001",
            precio_referencia="12000",
        )

        csv_content = "\n".join([
            "sku,precio,descuento_maximo",
            f"{producto.sku},10990,6",
        ])
        file = SimpleUploadedFile("lista_precios.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = api_client.post(
            reverse("lista-precio-bulk-import", args=[lista.id]),
            {"file": file, "dry_run": "true"},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["dry_run"] is True
        assert response.data["created"] == 1
        assert response.data["updated"] == 0
        assert response.data["errors"] == []
        assert not ListaPrecioItem.all_objects.filter(empresa=empresa, lista=lista, producto=producto).exists()
