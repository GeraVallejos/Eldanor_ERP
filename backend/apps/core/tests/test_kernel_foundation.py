from decimal import Decimal

import pytest

from apps.core.exceptions import BusinessRuleError
from apps.core.services import AccountingBridge, DomainEventService, OutboxService, WorkflowService
from apps.core.models import DomainEvent, OutboxEvent, OutboxStatus
from apps.inventario.services.inventario_service import InventarioService
from apps.inventario.models.movimiento import TipoMovimiento
from apps.productos.models import Producto
from apps.core.tenant import set_current_empresa


@pytest.mark.django_db
class TestKernelFoundation:
    def test_workflow_service_valida_transiciones(self):
        transitions = {
            "BORRADOR": {"ENVIADO", "ANULADO"},
            "ENVIADO": {"APROBADO", "ANULADO"},
            "APROBADO": set(),
            "ANULADO": set(),
        }

        assert WorkflowService.assert_transition(
            current_state="BORRADOR",
            next_state="enviado",
            transitions=transitions,
        ) == "ENVIADO"

        with pytest.raises(BusinessRuleError):
            WorkflowService.assert_transition(
                current_state="APROBADO",
                next_state="BORRADOR",
                transitions=transitions,
            )

    def test_domain_event_idempotencia(self, empresa, usuario):
        event_1 = DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="TEST",
            aggregate_id=empresa.id,
            event_type="CREATED",
            payload={"a": 1},
            idempotency_key="evt:test:1",
            usuario=usuario,
        )
        event_2 = DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="TEST",
            aggregate_id=empresa.id,
            event_type="CREATED",
            payload={"a": 2},
            idempotency_key="evt:test:1",
            usuario=usuario,
        )

        assert event_1.id == event_2.id
        assert DomainEvent.all_objects.filter(empresa=empresa, idempotency_key="evt:test:1").count() == 1

    def test_outbox_dedup_claim_y_mark_sent(self, empresa, usuario):
        outbox_1 = OutboxService.enqueue(
            empresa=empresa,
            topic="test",
            event_name="X",
            payload={"x": 1},
            usuario=usuario,
            dedup_key="out:test:1",
        )
        outbox_2 = OutboxService.enqueue(
            empresa=empresa,
            topic="test",
            event_name="X",
            payload={"x": 2},
            usuario=usuario,
            dedup_key="out:test:1",
        )

        assert outbox_1.id == outbox_2.id

        claimed = OutboxService.claim_pending(empresa=empresa, limit=10)
        assert len(claimed) == 1
        assert claimed[0].status == OutboxStatus.PROCESSING

        OutboxService.mark_sent(event=claimed[0])
        claimed[0].refresh_from_db()
        assert claimed[0].status == OutboxStatus.SENT

    def test_accounting_bridge_publica_domain_event_y_outbox(self, empresa, usuario):
        outbox = AccountingBridge.request_entry(
            empresa=empresa,
            aggregate_type="PRESUPUESTO",
            aggregate_id=empresa.id,
            entry_payload={"debe": "1000", "haber": "1000"},
            usuario=usuario,
            dedup_key="acc:req:1",
        )

        assert outbox.topic == "contabilidad"
        assert OutboxEvent.all_objects.filter(empresa=empresa, topic="contabilidad").exists()
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            event_type="ACCOUNTING_ENTRY_REQUESTED",
        ).exists()

    def test_inventario_movimiento_publica_eventos(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            nombre="Producto Kernel",
            sku="KRN-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        mov = InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("2.00"),
            referencia="KERNEL-EVT",
            empresa=empresa,
            usuario=usuario,
        )

        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_type="INVENTARIO",
            aggregate_id=mov.id,
            event_type="INVENTARIO_MOVIMIENTO_REGISTRADO",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="inventario",
            event_name="INVENTARIO_MOVIMIENTO_REGISTRADO",
        ).exists()
