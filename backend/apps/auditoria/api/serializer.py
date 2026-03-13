from rest_framework import serializers

from apps.auditoria.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    creado_por_email = serializers.EmailField(source="creado_por.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_por_email",
            "module_code",
            "action_code",
            "event_type",
            "severity",
            "entity_type",
            "entity_id",
            "summary",
            "changes",
            "payload",
            "meta",
            "source",
            "request_id",
            "correlation_id",
            "ip_address",
            "user_agent",
            "idempotency_key",
            "previous_hash",
            "event_hash",
            "occurred_at",
            "creado_en",
        ]
        read_only_fields = fields
