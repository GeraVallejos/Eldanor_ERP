from apps.core.services.domain_event_service import DomainEventService
from apps.core.services.outbox_service import OutboxService


class AccountingBridge:
    """Puente para desacoplar modulos de negocio de la implementacion contable."""

    TOPIC = "contabilidad"
    EVENT_NAME = "ASIENTO_SOLICITADO"

    @staticmethod
    def request_entry(
        *,
        empresa,
        aggregate_type,
        aggregate_id,
        entry_payload,
        usuario=None,
        dedup_key="",
    ):
        """Solicita un asiento contable publicando evento de dominio y outbox."""
        domain_event = DomainEventService.record_event(
            empresa=empresa,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type="ACCOUNTING_ENTRY_REQUESTED",
            payload=entry_payload,
            meta={"source": "AccountingBridge"},
            idempotency_key=f"domain:{dedup_key}" if dedup_key else None,
            usuario=usuario,
        )

        outbox_event = OutboxService.enqueue(
            empresa=empresa,
            topic=AccountingBridge.TOPIC,
            event_name=AccountingBridge.EVENT_NAME,
            payload={
                "domain_event_id": str(domain_event.id),
                "aggregate_type": aggregate_type,
                "aggregate_id": str(aggregate_id),
                "entry": entry_payload,
            },
            usuario=usuario,
            dedup_key=f"outbox:{dedup_key}" if dedup_key else None,
        )

        return outbox_event
