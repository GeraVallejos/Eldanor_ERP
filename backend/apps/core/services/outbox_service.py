from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.models.outbox_event import OutboxEvent, OutboxStatus


class OutboxService:
    """Helper de outbox transaccional para integraciones asincronas confiables."""

    @staticmethod
    def enqueue(
        *,
        empresa,
        topic,
        event_name,
        payload,
        usuario=None,
        dedup_key=None,
        available_at=None,
    ):
        """Encola un evento de integracion; con dedup_key evita duplicados."""
        data = {
            "empresa": empresa,
            "creado_por": usuario,
            "topic": topic,
            "event_name": event_name,
            "payload": payload or {},
            "dedup_key": dedup_key,
            "available_at": available_at or timezone.now(),
        }

        if dedup_key:
            event, _ = OutboxEvent.all_objects.get_or_create(
                empresa=empresa,
                dedup_key=dedup_key,
                defaults=data,
            )
            return event

        return OutboxEvent.all_objects.create(**data)

    @staticmethod
    @transaction.atomic
    def claim_pending(*, empresa=None, limit=100):
        """Toma eventos pendientes con lock para procesamiento exclusivo."""
        now = timezone.now()
        queryset = OutboxEvent.all_objects.select_for_update(skip_locked=True).filter(
            status=OutboxStatus.PENDING,
            available_at__lte=now,
        )
        if empresa is not None:
            queryset = queryset.filter(empresa=empresa)

        events = list(queryset.order_by("available_at", "creado_en")[:limit])
        for event in events:
            event.status = OutboxStatus.PROCESSING
            event.attempts += 1
            event.save(update_fields=["status", "attempts"])
        return events

    @staticmethod
    def mark_sent(*, event):
        """Marca un evento outbox como enviado exitosamente."""
        event.status = OutboxStatus.SENT
        event.processed_at = timezone.now()
        event.last_error = ""
        event.save(update_fields=["status", "processed_at", "last_error"])

    @staticmethod
    def mark_failed(*, event, error_message, retry_in_seconds=60):
        """Marca fallo y programa reintento del evento outbox."""
        event.status = OutboxStatus.FAILED
        event.last_error = str(error_message or "")
        event.available_at = timezone.now() + timedelta(seconds=retry_in_seconds)
        event.save(update_fields=["status", "last_error", "available_at"])

    @staticmethod
    def requeue_failed(*, empresa=None):
        """Reencola eventos fallidos para una nueva ventana de procesamiento."""
        queryset = OutboxEvent.all_objects.filter(status=OutboxStatus.FAILED)
        if empresa is not None:
            queryset = queryset.filter(empresa=empresa)

        count = queryset.update(status=OutboxStatus.PENDING)
        return count
