from decimal import Decimal
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.models import AuditEvent
from apps.contactos.models import Cliente, Contacto, Proveedor
from apps.core.models import UserEmpresa
from apps.tesoreria.models import Moneda


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
class TestTesoreriaApi:
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

    def test_movimiento_bancario_desconciliar_revierte_saldo_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Desconciliacion API",
            rut="12312312-3",
            email="cliente_desconciliacion_api@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        cuenta_resp = api_client.post(
            reverse("cuenta-bancaria-list"),
            {
                "alias": "Banco Desconciliacion",
                "banco": "Banco Estado",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "987654321",
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
                "referencia": "CXC-API-BANCO-002",
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
                "referencia": "DEP-002",
                "descripcion": "Deposito cliente reversible",
                "tipo": "CREDITO",
                "monto": "40000",
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

        desconciliar_resp = api_client.post(
            reverse("movimiento-bancario-desconciliar", args=[movimiento_resp.data["id"]]),
            {},
            format="json",
        )
        assert desconciliar_resp.status_code == status.HTTP_200_OK, desconciliar_resp.data
        assert desconciliar_resp.data["conciliado"] is False
        assert desconciliar_resp.data["cuenta_por_cobrar"] is None
        assert desconciliar_resp.data["cuenta_por_pagar"] is None

        detalle_cxc = api_client.get(reverse("cuenta-por-cobrar-detail", args=[cxc_resp.data["id"]]))
        assert detalle_cxc.status_code == status.HTTP_200_OK, detalle_cxc.data
        assert Decimal(str(detalle_cxc.data["saldo"])) == Decimal("100000")
        assert detalle_cxc.data["estado"] == "PENDIENTE"
        assert AuditEvent.all_objects.filter(
            empresa=empresa,
            event_type="TESORERIA_MOVIMIENTO_CONCILIADO",
            entity_id=movimiento_resp.data["id"],
        ).exists()
        assert AuditEvent.all_objects.filter(
            empresa=empresa,
            event_type="TESORERIA_MOVIMIENTO_DESCONCILIADO",
            entity_id=movimiento_resp.data["id"],
        ).exists()

    def test_movimiento_bancario_conciliar_y_desconciliar_cxp_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Proveedor Conciliacion API",
            rut="76123456-0",
            email="proveedor_conciliacion_api@test.com",
        )
        proveedor = Proveedor.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        cuenta_resp = api_client.post(
            reverse("cuenta-bancaria-list"),
            {
                "alias": "Banco Proveedores",
                "banco": "Banco Estado",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "456789123",
                "titular": "Empresa Test",
                "moneda": str(clp.id),
                "saldo_referencial": "0",
                "activa": True,
            },
            format="json",
        )
        assert cuenta_resp.status_code == status.HTTP_201_CREATED, cuenta_resp.data

        cxp_resp = api_client.post(
            reverse("cuenta-por-pagar-list"),
            {
                "proveedor": str(proveedor.id),
                "moneda": str(clp.id),
                "referencia": "CXP-API-BANCO-001",
                "fecha_emision": "2026-03-12",
                "fecha_vencimiento": "2026-03-30",
                "monto_total": "80000",
                "saldo": "80000",
                "estado": "PENDIENTE",
            },
            format="json",
        )
        assert cxp_resp.status_code == status.HTTP_201_CREATED, cxp_resp.data

        movimiento_resp = api_client.post(
            reverse("movimiento-bancario-list"),
            {
                "cuenta_bancaria": str(cuenta_resp.data["id"]),
                "fecha": "2026-03-15",
                "referencia": "PAG-001",
                "descripcion": "Pago proveedor reversible",
                "tipo": "DEBITO",
                "monto": "30000",
            },
            format="json",
        )
        assert movimiento_resp.status_code == status.HTTP_201_CREATED, movimiento_resp.data

        conciliar_resp = api_client.post(
            reverse("movimiento-bancario-conciliar", args=[movimiento_resp.data["id"]]),
            {"cuenta_por_pagar": cxp_resp.data["id"]},
            format="json",
        )
        assert conciliar_resp.status_code == status.HTTP_200_OK, conciliar_resp.data
        assert conciliar_resp.data["conciliado"] is True
        assert str(conciliar_resp.data["cuenta_por_pagar"]) == cxp_resp.data["id"]

        detalle_cxp = api_client.get(reverse("cuenta-por-pagar-detail", args=[cxp_resp.data["id"]]))
        assert detalle_cxp.status_code == status.HTTP_200_OK, detalle_cxp.data
        assert Decimal(str(detalle_cxp.data["saldo"])) == Decimal("50000")
        assert detalle_cxp.data["estado"] == "PARCIAL"

        desconciliar_resp = api_client.post(
            reverse("movimiento-bancario-desconciliar", args=[movimiento_resp.data["id"]]),
            {},
            format="json",
        )
        assert desconciliar_resp.status_code == status.HTTP_200_OK, desconciliar_resp.data
        assert desconciliar_resp.data["conciliado"] is False
        assert desconciliar_resp.data["cuenta_por_cobrar"] is None
        assert desconciliar_resp.data["cuenta_por_pagar"] is None

        detalle_cxp = api_client.get(reverse("cuenta-por-pagar-detail", args=[cxp_resp.data["id"]]))
        assert detalle_cxp.status_code == status.HTTP_200_OK, detalle_cxp.data
        assert Decimal(str(detalle_cxp.data["saldo"])) == Decimal("80000")
        assert detalle_cxp.data["estado"] == "PENDIENTE"

    def test_reportes_aging_cxc_y_cxp_por_api(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        contacto_cliente = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Aging API",
            rut="11111111-1",
            email="cliente_aging_api@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto_cliente)

        contacto_proveedor = Contacto.objects.create(
            empresa=empresa,
            nombre="Proveedor Aging API",
            rut="76123456-0",
            email="proveedor_aging_api@test.com",
        )
        proveedor = Proveedor.objects.create(empresa=empresa, contacto=contacto_proveedor)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        cxc_resp = api_client.post(
            reverse("cuenta-por-cobrar-list"),
            {
                "cliente": str(cliente.id),
                "moneda": str(clp.id),
                "referencia": "CXC-AGING-001",
                "fecha_emision": "2026-03-01",
                "fecha_vencimiento": "2026-03-10",
                "monto_total": "50000",
                "saldo": "50000",
                "estado": "PENDIENTE",
            },
            format="json",
        )
        assert cxc_resp.status_code == status.HTTP_201_CREATED, cxc_resp.data

        cxp_resp = api_client.post(
            reverse("cuenta-por-pagar-list"),
            {
                "proveedor": str(proveedor.id),
                "moneda": str(clp.id),
                "referencia": "CXP-AGING-001",
                "fecha_emision": "2026-03-01",
                "fecha_vencimiento": "2026-04-15",
                "monto_total": "70000",
                "saldo": "70000",
                "estado": "PENDIENTE",
            },
            format="json",
        )
        assert cxp_resp.status_code == status.HTTP_201_CREATED, cxp_resp.data

        aging_cxc = api_client.get(reverse("cuenta-por-cobrar-aging"), {"fecha_corte": "2026-04-20"})
        assert aging_cxc.status_code == status.HTTP_200_OK, aging_cxc.data
        assert Decimal(str(aging_cxc.data["totales"]["31_60"])) == Decimal("50000")

        aging_cxp = api_client.get(reverse("cuenta-por-pagar-aging"), {"fecha_corte": "2026-04-20"})
        assert aging_cxp.status_code == status.HTTP_200_OK, aging_cxp.data
        assert Decimal(str(aging_cxp.data["totales"]["1_30"])) == Decimal("70000")

    def test_reportes_aging_rechazan_fecha_corte_invalida(self, api_client, owner_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        aging_cxc = api_client.get(reverse("cuenta-por-cobrar-aging"), {"fecha_corte": "20-04-2026"})
        assert aging_cxc.status_code == status.HTTP_400_BAD_REQUEST, aging_cxc.data
        assert aging_cxc.data["error_code"] == "VALIDATION_ERROR"

        aging_cxp = api_client.get(reverse("cuenta-por-pagar-aging"), {"fecha_corte": "abril-20-2026"})
        assert aging_cxp.status_code == status.HTTP_400_BAD_REQUEST, aging_cxp.data
        assert aging_cxp.data["error_code"] == "VALIDATION_ERROR"

    def test_reportes_aging_exigen_permiso_ver(self, api_client, empresa):
        User = get_user_model()
        user = User.objects.create_user(
            username="sin_permiso_aging",
            email="sin_permiso_aging@test.com",
            password="pass1234",
            empresa_activa=empresa,
        )
        UserEmpresa.objects.create(user=user, empresa=empresa, rol="VENDEDOR", activo=True)

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(user)}")

        aging_cxc = api_client.get(reverse("cuenta-por-cobrar-aging"))
        assert aging_cxc.status_code == status.HTTP_403_FORBIDDEN, aging_cxc.data
        assert aging_cxc.data["error_code"] == "PERMISSION_DENIED"

        aging_cxp = api_client.get(reverse("cuenta-por-pagar-aging"))
        assert aging_cxp.status_code == status.HTTP_403_FORBIDDEN, aging_cxp.data
        assert aging_cxp.data["error_code"] == "PERMISSION_DENIED"

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

    def test_movimiento_bancario_desconciliar_sin_conciliar_retorna_400(self, api_client, owner_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")

        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        cuenta_resp = api_client.post(
            reverse("cuenta-bancaria-list"),
            {
                "alias": "Banco No Conciliado",
                "banco": "Banco Estado",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "111222333",
                "titular": "Empresa Test",
                "moneda": str(clp.id),
                "saldo_referencial": "0",
                "activa": True,
            },
            format="json",
        )
        assert cuenta_resp.status_code == status.HTTP_201_CREATED, cuenta_resp.data

        movimiento_resp = api_client.post(
            reverse("movimiento-bancario-list"),
            {
                "cuenta_bancaria": str(cuenta_resp.data["id"]),
                "fecha": "2026-03-15",
                "referencia": "DEP-RAW-001",
                "descripcion": "Movimiento aun no conciliado",
                "tipo": "CREDITO",
                "monto": "15000",
            },
            format="json",
        )
        assert movimiento_resp.status_code == status.HTTP_201_CREATED, movimiento_resp.data

        response = api_client.post(
            reverse("movimiento-bancario-desconciliar", args=[movimiento_resp.data["id"]]),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        assert response.data["error_code"] == "BANK_MOVEMENT_NOT_RECONCILED"

    def test_movimiento_bancario_conciliar_exige_permiso_conciliar(self, api_client, owner_usuario, empresa):
        User = get_user_model()
        user = User.objects.create_user(
            username="sin_permiso_conciliar",
            email="sin_permiso_conciliar@test.com",
            password="pass1234",
            empresa_activa=empresa,
        )
        UserEmpresa.objects.create(user=user, empresa=empresa, rol="VENDEDOR", activo=True)

        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Permisos Tesoreria",
            rut="12312312-3",
            email="cliente_permiso_tesoreria@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(owner_usuario)}")
        cuenta_resp = api_client.post(
            reverse("cuenta-bancaria-list"),
            {
                "alias": "Banco Permisos",
                "banco": "Banco Estado",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "333222111",
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
                "referencia": "CXC-PERM-001",
                "fecha_emision": "2026-03-12",
                "fecha_vencimiento": "2026-03-30",
                "monto_total": "10000",
                "saldo": "10000",
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
                "referencia": "DEP-PERM-001",
                "descripcion": "Movimiento para probar permiso",
                "tipo": "CREDITO",
                "monto": "10000",
            },
            format="json",
        )
        assert movimiento_resp.status_code == status.HTTP_201_CREATED, movimiento_resp.data

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(user)}")
        response = api_client.post(
            reverse("movimiento-bancario-conciliar", args=[movimiento_resp.data["id"]]),
            {"cuenta_por_cobrar": cxc_resp.data["id"]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
        assert response.data["error_code"] == "PERMISSION_DENIED"
