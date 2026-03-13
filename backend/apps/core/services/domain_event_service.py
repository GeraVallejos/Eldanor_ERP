from apps.core.models.domain_event import DomainEvent


class DomainEventService:
    """Registrador centralizado de eventos de dominio append-only."""

    @staticmethod
    def record_event(
        *,
        empresa,
        aggregate_type,
        aggregate_id,
        event_type,
        payload=None,
        meta=None,
        idempotency_key=None,
        usuario=None,
        event_version=1,
    ):
        """Persiste un evento de dominio con soporte opcional de idempotencia."""
        data = {
            "empresa": empresa,
            "creado_por": usuario,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "event_type": event_type,
            "event_version": event_version,
            "payload": payload or {},
            "meta": meta or {},
            "idempotency_key": idempotency_key,
        }

        if idempotency_key:
            event, _ = DomainEvent.all_objects.get_or_create(
                empresa=empresa,
                idempotency_key=idempotency_key,
                defaults=data,
            )
            return event

        return DomainEvent.all_objects.create(**data)
