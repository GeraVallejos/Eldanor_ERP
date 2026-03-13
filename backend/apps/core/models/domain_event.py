from django.db import models
from apps.core.exceptions import BusinessRuleError
from apps.core.models.base import BaseModel


class DomainEvent(BaseModel):
    """Append-only tenant-scoped domain event for business traceability."""

    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.UUIDField()
    event_type = models.CharField(max_length=120)
    event_version = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True, null=True, default=None)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "aggregate_type", "aggregate_id", "occurred_at"]),
            models.Index(fields=["empresa", "event_type", "occurred_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "idempotency_key"],
                name="uniq_domain_event_idempotency_per_empresa",
            )
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise BusinessRuleError("DomainEvent es append-only y no puede modificarse.")
        super().save(*args, **kwargs)
