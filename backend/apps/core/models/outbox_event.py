from django.db import models
from django.utils import timezone

from apps.core.models.base import BaseModel


class OutboxStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class OutboxEvent(BaseModel):
    """Transactional outbox entry for reliable cross-module/integration messaging."""

    topic = models.CharField(max_length=80)
    event_name = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=OutboxStatus.choices, default=OutboxStatus.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    dedup_key = models.CharField(max_length=120, blank=True, null=True, default=None)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "status", "available_at"]),
            models.Index(fields=["empresa", "topic", "creado_en"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "dedup_key"],
                name="uniq_outbox_dedup_per_empresa",
            )
        ]
