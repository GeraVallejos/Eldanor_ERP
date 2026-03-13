import hashlib
import json

from django.db import models

from apps.core.exceptions import BusinessRuleError
from apps.core.models.base import BaseModel


class AuditSeverity(models.TextChoices):
	INFO = "INFO", "Info"
	WARNING = "WARNING", "Warning"
	ERROR = "ERROR", "Error"
	CRITICAL = "CRITICAL", "Critical"


class AuditEvent(BaseModel):
	"""Evento de auditoria central ERP con inmutabilidad e integridad encadenada."""

	module_code = models.CharField(max_length=60)
	action_code = models.CharField(max_length=80)
	event_type = models.CharField(max_length=120)
	severity = models.CharField(max_length=20, choices=AuditSeverity.choices, default=AuditSeverity.INFO)

	entity_type = models.CharField(max_length=80)
	entity_id = models.CharField(max_length=64, blank=True, default="")

	summary = models.CharField(max_length=255)
	changes = models.JSONField(default=dict, blank=True)
	payload = models.JSONField(default=dict, blank=True)
	meta = models.JSONField(default=dict, blank=True)

	source = models.CharField(max_length=120, blank=True, default="")
	request_id = models.CharField(max_length=80, blank=True, null=True, default=None)
	correlation_id = models.CharField(max_length=80, blank=True, null=True, default=None)
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.CharField(max_length=255, blank=True, default="")

	idempotency_key = models.CharField(max_length=120, blank=True, null=True, default=None)
	previous_hash = models.CharField(max_length=64, blank=True, default="")
	event_hash = models.CharField(max_length=64, editable=False, db_index=True)
	occurred_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		indexes = [
			models.Index(fields=["empresa", "module_code", "occurred_at"]),
			models.Index(fields=["empresa", "event_type", "occurred_at"]),
			models.Index(fields=["empresa", "entity_type", "entity_id", "occurred_at"]),
		]
		constraints = [
			models.UniqueConstraint(
				fields=["empresa", "idempotency_key"],
				name="uniq_audit_event_idempotency_per_empresa",
			)
		]

	@staticmethod
	def _normalize_json(value):
		return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)

	def compute_event_hash(self):
		"""Calcula hash deterministico del evento con cadena previa para integridad."""
		raw = "|".join(
			[
				str(self.id),
				str(self.empresa_id),
				str(self.creado_por_id or ""),
				self.module_code,
				self.action_code,
				self.event_type,
				self.severity,
				self.entity_type,
				self.entity_id or "",
				self.summary,
				self.source or "",
				self.request_id or "",
				self.correlation_id or "",
				self.ip_address or "",
				self.user_agent or "",
				self.idempotency_key or "",
				self.previous_hash or "",
				self._normalize_json(self.changes),
				self._normalize_json(self.payload),
				self._normalize_json(self.meta),
			]
		)
		return hashlib.sha256(raw.encode("utf-8")).hexdigest()

	def save(self, *args, **kwargs):
		if not self._state.adding:
			raise BusinessRuleError("AuditEvent es append-only y no puede modificarse.")
		if not self.event_hash:
			self.event_hash = self.compute_event_hash()
		super().save(*args, **kwargs)
