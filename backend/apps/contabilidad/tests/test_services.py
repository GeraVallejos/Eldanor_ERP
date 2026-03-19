from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.contabilidad.models import EstadoAsientoContable
from apps.contabilidad.services import ContabilidadService
from apps.core.exceptions import BusinessRuleError
from apps.core.models import DomainEvent, OutboxEvent, OutboxStatus, UserEmpresa
from apps.core.services.accounting_bridge import AccountingBridge
from apps.core.tenant import set_current_empresa, set_current_user


@pytest.fixture
def usuario_owner_contabilidad(db, empresa):
    User = get_user_model()
    user = User.objects.create_user(
        username="owner_contabilidad_service",
        email="owner_contabilidad_service@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.mark.django_db
class TestContabilidadService:
    def test_seed_plan_base_crea_cuentas(self, empresa, usuario_owner_contabilidad):
        set_current_empresa(empresa)
        set_current_user(usuario_owner_contabilidad)

        creadas = ContabilidadService.seed_plan_base(
            empresa=empresa,
            usuario=usuario_owner_contabilidad,
        )

        assert len(creadas) == len(ContabilidadService.CODIGOS_BASE)

    def test_crear_asiento_y_contabilizar(self, empresa, usuario_owner_contabilidad):
        set_current_empresa(empresa)
        set_current_user(usuario_owner_contabilidad)

        ContabilidadService.seed_plan_base(empresa=empresa, usuario=usuario_owner_contabilidad)
        clientes = ContabilidadService._buscar_cuenta_por_codigo(empresa=empresa, codigo="112100")
        ventas = ContabilidadService._buscar_cuenta_por_codigo(empresa=empresa, codigo="411100")

        asiento = ContabilidadService.crear_asiento(
            empresa=empresa,
            fecha=date(2026, 3, 19),
            glosa="Factura manual",
            movimientos_data=[
                {"cuenta": clientes, "debe": "1190", "haber": "0"},
                {"cuenta": ventas, "debe": "0", "haber": "1190"},
            ],
            usuario=usuario_owner_contabilidad,
        )

        assert asiento.cuadrado is True
        assert asiento.total_debe == Decimal("1190.00")
        assert asiento.total_haber == Decimal("1190.00")

        asiento = ContabilidadService.contabilizar_asiento(
            asiento_id=asiento.id,
            empresa=empresa,
            usuario=usuario_owner_contabilidad,
        )

        assert asiento.estado == EstadoAsientoContable.CONTABILIZADO
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_id=asiento.id,
            event_type="contabilidad.asiento_contabilizado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="contabilidad.asiento",
            event_name="asiento.contabilizado",
        ).exists()

    def test_no_contabiliza_asiento_descuadrado(self, empresa, usuario_owner_contabilidad):
        set_current_empresa(empresa)
        set_current_user(usuario_owner_contabilidad)

        ContabilidadService.seed_plan_base(empresa=empresa, usuario=usuario_owner_contabilidad)
        clientes = ContabilidadService._buscar_cuenta_por_codigo(empresa=empresa, codigo="112100")
        ventas = ContabilidadService._buscar_cuenta_por_codigo(empresa=empresa, codigo="411100")

        asiento = ContabilidadService.crear_asiento(
            empresa=empresa,
            fecha=date(2026, 3, 19),
            glosa="Asiento descuadrado",
            movimientos_data=[
                {"cuenta": clientes, "debe": "1000", "haber": "0"},
                {"cuenta": ventas, "debe": "0", "haber": "900"},
            ],
            usuario=usuario_owner_contabilidad,
        )

        with pytest.raises(BusinessRuleError):
            ContabilidadService.contabilizar_asiento(
                asiento_id=asiento.id,
                empresa=empresa,
                usuario=usuario_owner_contabilidad,
            )

    def test_procesar_solicitud_pendiente_desde_accounting_bridge(self, empresa, usuario_owner_contabilidad):
        set_current_empresa(empresa)
        set_current_user(usuario_owner_contabilidad)

        ContabilidadService.seed_plan_base(empresa=empresa, usuario=usuario_owner_contabilidad)

        evento = AccountingBridge.request_entry(
            empresa=empresa,
            aggregate_type="FacturaVenta",
            aggregate_id="11111111-1111-1111-1111-111111111111",
            entry_payload={
                "fecha": "2026-03-19",
                "glosa": "Factura automatica",
                "referencia_tipo": "FACTURA_VENTA",
                "movimientos": [
                    {"cuenta_codigo": "112100", "debe": "1190", "haber": "0"},
                    {"cuenta_codigo": "411100", "debe": "0", "haber": "1000"},
                    {"cuenta_codigo": "213100", "debe": "0", "haber": "190"},
                ],
            },
            usuario=usuario_owner_contabilidad,
            dedup_key="test-accounting-bridge",
        )

        procesados = ContabilidadService.procesar_solicitudes_pendientes(
            empresa=empresa,
            usuario=usuario_owner_contabilidad,
        )

        assert len(procesados) == 1
        assert procesados[0].estado == EstadoAsientoContable.CONTABILIZADO
        evento.refresh_from_db()
        assert evento.status == OutboxStatus.SENT

