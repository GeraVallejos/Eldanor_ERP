import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.models import AuditEvent
from apps.contactos.models import Cliente, Contacto, CuentaBancaria, Direccion, Proveedor
from apps.core.models import UserEmpresa
from apps.core.roles import RolUsuario


def _token(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.fixture
def admin_usuario(db, empresa):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"admin_contactos_{suffix}",
        email=f"admin_contactos_{suffix}@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="ADMIN", activo=True)
    return user


@pytest.fixture
def contador_usuario(db, empresa):
    User = get_user_model()
    suffix = uuid.uuid4().hex[:8]
    user = User.objects.create_user(
        username=f"contador_contactos_{suffix}",
        email=f"contador_contactos_{suffix}@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol=RolUsuario.CONTADOR, activo=True)
    return user


@pytest.mark.django_db
class TestContactosAuditoriaApi:
    def test_contacto_crud_registra_auditoria(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        create_response = api_client.post(
            reverse("contacto-list"),
            {
                "nombre": "Contacto Auditoria",
                "rut": "11111111-1",
                "tipo": "EMPRESA",
                "email": "contacto.auditoria@test.com",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        contacto_id = create_response.data["id"]

        update_response = api_client.patch(
            reverse("contacto-detail", args=[contacto_id]),
            {"telefono": "99999999"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK

        delete_response = api_client.delete(reverse("contacto-detail", args=[contacto_id]))
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        eventos = AuditEvent.all_objects.filter(empresa=empresa, entity_type="CONTACTO")
        event_types = set(eventos.values_list("event_type", flat=True))

        assert "CONTACTO_CREADO" in event_types
        assert "CONTACTO_ACTUALIZADO" in event_types
        assert "CONTACTO_ELIMINADO" in event_types

    def test_cliente_y_proveedor_registran_auditoria(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Contacto Base",
            rut="22222222-2",
            tipo="EMPRESA",
            email="contacto.base@test.com",
        )

        cliente_response = api_client.post(
            reverse("cliente-list"),
            {
                "contacto": str(contacto.id),
                "limite_credito": "100000",
                "dias_credito": 15,
            },
            format="json",
        )
        assert cliente_response.status_code == status.HTTP_201_CREATED

        proveedor_response = api_client.post(
            reverse("proveedor-list"),
            {
                "contacto": str(contacto.id),
                "giro": "Servicios",
                "dias_credito": 20,
            },
            format="json",
        )
        assert proveedor_response.status_code == status.HTTP_201_CREATED

        assert AuditEvent.all_objects.filter(empresa=empresa, event_type="CLIENTE_CREADO").exists()
        assert AuditEvent.all_objects.filter(empresa=empresa, event_type="PROVEEDOR_CREADO").exists()

    def test_contacto_api_rechaza_campos_maestros_faltantes(self, api_client, admin_usuario):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        response = api_client.post(
            reverse("contacto-list"),
            {
                "nombre": "Contacto incompleto",
                "rut": "",
                "tipo": "",
                "email": "",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "rut" in response.data["detail"]
        assert "email" in response.data["detail"]
        assert "tipo" in response.data["detail"]

    def test_detalle_tercero_expone_ficha_consolidada(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="TERCERO CONSOLIDADO",
            rut="12345678-5",
            tipo="EMPRESA",
            email="consolidado@test.com",
            telefono="22223333",
            activo=True,
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="150000",
            dias_credito=20,
            categoria_cliente="ORO",
        )
        proveedor = Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="SERVICIOS",
            dias_credito=15,
        )
        direccion = Direccion.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            tipo="COMERCIAL",
            direccion="AV. ERP 123",
            comuna="PROVIDENCIA",
            ciudad="SANTIAGO",
            region="RM",
            pais="CHILE",
        )
        cuenta = CuentaBancaria.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            banco="BANCO ESTADO",
            tipo_cuenta="CORRIENTE",
            numero_cuenta="123456",
            titular="TERCERO CONSOLIDADO",
            rut_titular="12.345.678-5",
            activa=True,
        )

        response = api_client.get(reverse("contacto-detalle-tercero", args=[contacto.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(contacto.id)
        assert response.data["cliente"]["id"] == str(cliente.id)
        assert response.data["proveedor"]["id"] == str(proveedor.id)
        assert len(response.data["direcciones"]) == 1
        assert response.data["direcciones"][0]["id"] == str(direccion.id)
        assert len(response.data["cuentas_bancarias"]) == 1
        assert response.data["cuentas_bancarias"][0]["id"] == str(cuenta.id)

    def test_listado_clientes_expone_contacto_resumen_embebido(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="CLIENTE RESUMIDO",
            rut="11111111-1",
            tipo="EMPRESA",
            email="resumido@test.com",
            telefono="22334455",
            activo=True,
        )
        Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="90000",
            dias_credito=30,
        )

        response = api_client.get(reverse("cliente-list"))

        assert response.status_code == status.HTTP_200_OK
        row = response.data[0]
        assert str(row["contacto"]) == str(contacto.id)
        assert row["contacto_resumen"]["id"] == str(contacto.id)
        assert row["contacto_resumen"]["nombre"] == "CLIENTE RESUMIDO"
        assert row["contacto_resumen"]["rut"] == "11.111.111-1"
        assert row["contacto_resumen"]["email"] == "resumido@test.com"

    def test_listado_proveedores_expone_contacto_resumen_embebido(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="PROVEEDOR RESUMIDO",
            rut="22.222.222-2",
            tipo="EMPRESA",
            email="proveedor.resumido@test.com",
            telefono="99887766",
            activo=True,
        )
        Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="SUMINISTROS",
            dias_credito=20,
        )

        response = api_client.get(reverse("proveedor-list"))

        assert response.status_code == status.HTTP_200_OK
        row = response.data[0]
        assert str(row["contacto"]) == str(contacto.id)
        assert row["contacto_resumen"]["id"] == str(contacto.id)
        assert row["contacto_resumen"]["nombre"] == "PROVEEDOR RESUMIDO"
        assert row["contacto_resumen"]["rut"] == "22.222.222-2"
        assert row["contacto_resumen"]["email"] == "proveedor.resumido@test.com"

    def test_detalle_edicion_cliente_expone_contacto_embebido(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="CLIENTE EDICION",
            rut="22222222-2",
            tipo="EMPRESA",
            email="cliente.edicion@test.com",
            activo=True,
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="100000",
            dias_credito=25,
            categoria_cliente="PLATA",
        )

        response = api_client.get(reverse("cliente-detalle-edicion", args=[cliente.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(cliente.id)
        assert response.data["contacto"]["id"] == str(contacto.id)
        assert response.data["contacto"]["nombre"] == "CLIENTE EDICION"
        assert response.data["categoria_cliente"] == "PLATA"

    def test_detalle_edicion_proveedor_expone_contacto_embebido(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="PROVEEDOR EDICION",
            rut="33333333-3",
            tipo="EMPRESA",
            email="proveedor.edicion@test.com",
            activo=True,
        )
        proveedor = Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="SERVICIOS",
            vendedor_contacto="ANA PEREZ",
            dias_credito=20,
        )

        response = api_client.get(reverse("proveedor-detalle-edicion", args=[proveedor.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(proveedor.id)
        assert response.data["contacto"]["id"] == str(contacto.id)
        assert response.data["contacto"]["nombre"] == "PROVEEDOR EDICION"
        assert response.data["giro"] == "SERVICIOS"

    def test_actualizar_cliente_con_contacto_es_atomico_desde_endpoint_compuesto(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="CLIENTE ORIGINAL",
            rut="44444444-4",
            tipo="EMPRESA",
            email="cliente.original@test.com",
            activo=True,
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="90000",
            dias_credito=30,
            segmento="RETAIL",
        )

        response = api_client.patch(
            reverse("cliente-actualizar-con-contacto", args=[cliente.id]),
            {
                "nombre": "CLIENTE ACTUALIZADO",
                "rut": "44.444.444-4",
                "tipo": "EMPRESA",
                "email": "cliente.actualizado@test.com",
                "activo": True,
                "limite_credito": "150000",
                "dias_credito": 45,
                "segmento": "CORPORATIVO",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        contacto.refresh_from_db()
        cliente.refresh_from_db()
        assert contacto.nombre == "CLIENTE ACTUALIZADO"
        assert contacto.email == "cliente.actualizado@test.com"
        assert str(cliente.limite_credito) == "150000.00"
        assert cliente.segmento == "CORPORATIVO"

    def test_actualizar_cliente_con_contacto_acepta_patch_parcial(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="CLIENTE PARCIAL",
            rut="11.111.111-1",
            tipo="EMPRESA",
            email="cliente.parcial@test.com",
            activo=True,
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="70000",
            dias_credito=15,
            segmento="PYME",
        )

        response = api_client.patch(
            reverse("cliente-actualizar-con-contacto", args=[cliente.id]),
            {
                "limite_credito": "95000",
                "dias_credito": 21,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        contacto.refresh_from_db()
        cliente.refresh_from_db()
        assert contacto.nombre == "CLIENTE PARCIAL"
        assert contacto.email == "cliente.parcial@test.com"
        assert str(cliente.limite_credito) == "95000.00"
        assert cliente.dias_credito == 21

    def test_actualizar_proveedor_con_contacto_es_atomico_desde_endpoint_compuesto(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="PROVEEDOR ORIGINAL",
            rut="55555555-5",
            tipo="EMPRESA",
            email="proveedor.original@test.com",
            activo=True,
        )
        proveedor = Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="SERVICIOS",
            vendedor_contacto="ANA PEREZ",
            dias_credito=15,
        )

        response = api_client.patch(
            reverse("proveedor-actualizar-con-contacto", args=[proveedor.id]),
            {
                "nombre": "PROVEEDOR ACTUALIZADO",
                "rut": "55.555.555-5",
                "tipo": "EMPRESA",
                "email": "proveedor.actualizado@test.com",
                "activo": True,
                "giro": "SERVICIOS INDUSTRIALES",
                "vendedor_contacto": "BEATRIZ SOTO",
                "dias_credito": 40,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        contacto.refresh_from_db()
        proveedor.refresh_from_db()
        assert contacto.nombre == "PROVEEDOR ACTUALIZADO"
        assert contacto.email == "proveedor.actualizado@test.com"
        assert proveedor.giro == "SERVICIOS INDUSTRIALES"
        assert proveedor.dias_credito == 40

    def test_actualizar_proveedor_con_contacto_acepta_patch_parcial(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="PROVEEDOR PARCIAL",
            rut="22.222.222-2",
            tipo="EMPRESA",
            email="proveedor.parcial@test.com",
            activo=True,
        )
        proveedor = Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="SERVICIOS BASE",
            vendedor_contacto="ANA BASE",
            dias_credito=18,
        )

        response = api_client.patch(
            reverse("proveedor-actualizar-con-contacto", args=[proveedor.id]),
            {
                "giro": "SERVICIOS PARCIALES",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        contacto.refresh_from_db()
        proveedor.refresh_from_db()
        assert contacto.nombre == "PROVEEDOR PARCIAL"
        assert contacto.email == "proveedor.parcial@test.com"
        assert proveedor.giro == "SERVICIOS PARCIALES"
        assert proveedor.vendedor_contacto == "ANA BASE"

    def test_contacto_auditoria_consolida_eventos_relacionados(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="TERCERO AUDITADO",
            rut="66666666-6",
            tipo="EMPRESA",
            email="auditado@test.com",
            activo=True,
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="100000",
            dias_credito=30,
        )
        direccion = Direccion.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            tipo="COMERCIAL",
            direccion="AV. AUDIT 123",
            comuna="PROVIDENCIA",
            ciudad="SANTIAGO",
            region="RM",
            pais="CHILE",
        )
        cuenta = CuentaBancaria.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            banco="BANCO ESTADO",
            tipo_cuenta="CORRIENTE",
            numero_cuenta="123456",
            titular="TERCERO AUDITADO",
            rut_titular="66.666.666-6",
            activa=True,
        )

        AuditEvent.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            module_code="CONTACTOS",
            action_code="VER",
            event_type="CONTACTO_ACTUALIZADO",
            entity_type="CONTACTO",
            entity_id=str(contacto.id),
            summary="Contacto actualizado",
            severity="INFO",
        )
        AuditEvent.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            module_code="CONTACTOS",
            action_code="EDITAR",
            event_type="CLIENTE_ACTUALIZADO",
            entity_type="CLIENTE",
            entity_id=str(cliente.id),
            summary="Cliente actualizado",
            severity="WARNING",
        )
        AuditEvent.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            module_code="CONTACTOS",
            action_code="EDITAR",
            event_type="DIRECCION_ACTUALIZADA",
            entity_type="DIRECCION",
            entity_id=str(direccion.id),
            summary="Direccion actualizada",
            severity="ERROR",
        )
        AuditEvent.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            module_code="CONTACTOS",
            action_code="EDITAR",
            event_type="CUENTA_BANCARIA_ACTUALIZADA",
            entity_type="CUENTA_BANCARIA",
            entity_id=str(cuenta.id),
            summary="Cuenta actualizada",
            severity="CRITICAL",
        )

        response = api_client.get(reverse("contacto-auditoria", args=[contacto.id]))

        assert response.status_code == status.HTTP_200_OK
        event_types = {row["event_type"] for row in response.data}
        assert "CONTACTO_ACTUALIZADO" in event_types
        assert "CLIENTE_ACTUALIZADO" in event_types
        assert "DIRECCION_ACTUALIZADA" in event_types
        assert "CUENTA_BANCARIA_ACTUALIZADA" in event_types

    def test_acciones_custom_rechazan_usuario_sin_permiso_contactos(self, api_client, contador_usuario, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(contador_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="TERCERO RESTRINGIDO",
            rut="33.333.333-3",
            tipo="EMPRESA",
            email="restringido@test.com",
            activo=True,
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="50000",
            dias_credito=15,
        )
        proveedor = Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="SERVICIOS",
            dias_credito=10,
        )

        responses = [
            api_client.get(reverse("contacto-detalle-tercero", args=[contacto.id])),
            api_client.get(reverse("contacto-auditoria", args=[contacto.id])),
            api_client.get(reverse("cliente-detalle-edicion", args=[cliente.id])),
            api_client.patch(
                reverse("cliente-actualizar-con-contacto", args=[cliente.id]),
                {
                    "nombre": "INTENTO BLOQUEADO",
                    "rut": "33.333.333-3",
                    "tipo": "EMPRESA",
                    "email": "bloqueado@test.com",
                    "activo": True,
                    "limite_credito": "55000",
                    "dias_credito": 20,
                },
                format="json",
            ),
            api_client.get(reverse("proveedor-detalle-edicion", args=[proveedor.id])),
            api_client.patch(
                reverse("proveedor-actualizar-con-contacto", args=[proveedor.id]),
                {
                    "nombre": "PROVEEDOR BLOQUEADO",
                    "rut": "33.333.333-3",
                    "tipo": "EMPRESA",
                    "email": "proveedor.bloqueado@test.com",
                    "activo": True,
                    "giro": "SERVICIOS CRITICOS",
                    "dias_credito": 25,
                },
                format="json",
            ),
        ]

        for response in responses:
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.data["error_code"] == "PERMISSION_DENIED"

    def test_eliminar_cliente_borra_contacto_si_no_tiene_otras_relaciones(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Cliente Orfano",
            rut="33333333-3",
            tipo="EMPRESA",
            email="cliente.orfano@test.com",
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="150000",
            dias_credito=20,
        )

        response = api_client.delete(reverse("cliente-detail", args=[cliente.id]))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Cliente.all_objects.filter(id=cliente.id).exists()
        assert not Contacto.all_objects.filter(id=contacto.id).exists()
        assert AuditEvent.all_objects.filter(empresa=empresa, event_type="CLIENTE_ELIMINADO").exists()
        assert AuditEvent.all_objects.filter(empresa=empresa, event_type="CONTACTO_ELIMINADO").exists()

    def test_eliminar_cliente_conserva_contacto_si_tambien_es_proveedor(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="Cliente Proveedor",
            rut="44444444-4",
            tipo="EMPRESA",
            email="cliente.proveedor@test.com",
        )
        cliente = Cliente.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            limite_credito="250000",
            dias_credito=30,
        )
        Proveedor.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            contacto=contacto,
            giro="Servicios",
            dias_credito=10,
        )

        response = api_client.delete(reverse("cliente-detail", args=[cliente.id]))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Cliente.all_objects.filter(id=cliente.id).exists()
        assert Contacto.all_objects.filter(id=contacto.id).exists()

    def test_crear_contacto_reutiliza_y_reactiva_registro_existente_por_rut(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="TERCERO INACTIVO",
            rut="55555555-5",
            tipo="EMPRESA",
            email="inactivo@test.com",
            activo=False,
        )

        response = api_client.post(
            reverse("contacto-list"),
            {
                "nombre": "Tercero Reactivado",
                "rut": "55.555.555-5",
                "tipo": "EMPRESA",
                "email": "reactivado@test.com",
                "activo": True,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["id"] == str(contacto.id)

        contacto.refresh_from_db()
        assert contacto.nombre == "TERCERO REACTIVADO"
        assert contacto.email == "reactivado@test.com"
        assert contacto.activo is True
        assert Contacto.all_objects.filter(empresa=empresa, rut="55.555.555-5").count() == 1

        evento = AuditEvent.all_objects.filter(
            empresa=empresa,
            event_type="CONTACTO_ACTUALIZADO",
            entity_id=str(contacto.id),
        ).latest("creado_en")
        assert evento.payload["reused_existing"] is True
        assert evento.payload["reactivated"] is True

    def test_crear_cliente_con_contacto_reutiliza_rut_existente_desde_endpoint_compuesto(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="CLIENTE BASE",
            rut="66666666-6",
            tipo="EMPRESA",
            email="cliente.base@test.com",
            activo=False,
        )

        response = api_client.post(
            reverse("cliente-crear-con-contacto"),
            {
                "nombre": "Cliente Reactivado",
                "rut": "66.666.666-6",
                "tipo": "EMPRESA",
                "email": "cliente.reactivado@test.com",
                "activo": True,
                "limite_credito": "200000",
                "dias_credito": 45,
                "categoria_cliente": "ORO",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        contacto.refresh_from_db()
        assert contacto.nombre == "CLIENTE REACTIVADO"
        assert contacto.email == "cliente.reactivado@test.com"
        assert contacto.activo is True
        assert Contacto.all_objects.filter(empresa=empresa, rut="66.666.666-6").count() == 1

        cliente = Cliente.all_objects.get(id=response.data["id"])
        assert cliente.contacto_id == contacto.id
        assert str(cliente.limite_credito) == "200000.00"
        assert cliente.dias_credito == 45

    def test_direccion_crud_registra_auditoria(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="TERCERO DIRECCION",
            rut="77777777-7",
            tipo="EMPRESA",
            email="direccion@test.com",
        )

        create_response = api_client.post(
            reverse("direccion-list"),
            {
                "contacto": str(contacto.id),
                "tipo": "COMERCIAL",
                "direccion": "Av. Nueva 123",
                "comuna": "Providencia",
                "ciudad": "Santiago",
                "region": "RM",
                "pais": "CHILE",
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        direccion_id = create_response.data["id"]

        update_response = api_client.patch(
            reverse("direccion-detail", args=[direccion_id]),
            {"ciudad": "Las Condes"},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK

        delete_response = api_client.delete(reverse("direccion-detail", args=[direccion_id]))
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        event_types = set(
            AuditEvent.all_objects.filter(empresa=empresa, entity_type="DIRECCION").values_list("event_type", flat=True)
        )
        assert "DIRECCION_CREADA" in event_types
        assert "DIRECCION_ACTUALIZADA" in event_types
        assert "DIRECCION_ELIMINADA" in event_types

    def test_cuenta_bancaria_crud_registra_auditoria(self, api_client, admin_usuario, empresa):
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(admin_usuario)}")

        contacto = Contacto.all_objects.create(
            empresa=empresa,
            creado_por=admin_usuario,
            nombre="TERCERO BANCO",
            rut="88888888-8",
            tipo="EMPRESA",
            email="banco@test.com",
        )

        create_response = api_client.post(
            reverse("contacto-cuenta-bancaria-list"),
            {
                "contacto": str(contacto.id),
                "banco": "BANCO ESTADO",
                "tipo_cuenta": "CORRIENTE",
                "numero_cuenta": "123456",
                "titular": "TERCERO BANCO",
                "rut_titular": "88.888.888-8",
                "activa": True,
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        cuenta_id = create_response.data["id"]

        update_response = api_client.patch(
            reverse("contacto-cuenta-bancaria-detail", args=[cuenta_id]),
            {"activa": False},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK

        delete_response = api_client.delete(reverse("contacto-cuenta-bancaria-detail", args=[cuenta_id]))
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT

        event_types = set(
            AuditEvent.all_objects.filter(empresa=empresa, entity_type="CUENTA_BANCARIA").values_list("event_type", flat=True)
        )
        assert "CUENTA_BANCARIA_CREADA" in event_types
        assert "CUENTA_BANCARIA_ACTUALIZADA" in event_types
        assert "CUENTA_BANCARIA_ELIMINADA" in event_types
