from django.db import IntegrityError, transaction

from apps.auditoria.models import AuditEvent, AuditSeverity
from apps.core.exceptions import BusinessRuleError


class AuditoriaService:
    """Servicio central para registrar y consultar auditoria funcional del ERP."""

    @staticmethod
    def _validate_required(*, module_code, action_code, event_type, entity_type):
        if not str(module_code or "").strip():
            raise BusinessRuleError("module_code es obligatorio para registrar auditoria.")
        if not str(action_code or "").strip():
            raise BusinessRuleError("action_code es obligatorio para registrar auditoria.")
        if not str(event_type or "").strip():
            raise BusinessRuleError("event_type es obligatorio para registrar auditoria.")
        if not str(entity_type or "").strip():
            raise BusinessRuleError("entity_type es obligatorio para registrar auditoria.")

    @staticmethod
    @transaction.atomic
    def registrar_evento(
        *,
        empresa,
        usuario,
        module_code,
        action_code,
        event_type,
        entity_type,
        entity_id=None,
        summary="",
        severity=AuditSeverity.INFO,
        changes=None,
        payload=None,
        meta=None,
        source="",
        request_id=None,
        correlation_id=None,
        ip_address=None,
        user_agent="",
        idempotency_key=None,
    ):
        """Registra un evento append-only con hash chain por empresa e idempotencia opcional."""
        AuditoriaService._validate_required(
            module_code=module_code,
            action_code=action_code,
            event_type=event_type,
            entity_type=entity_type,
        )

        normalized_severity = str(severity or AuditSeverity.INFO).upper()
        valid_severities = {choice for choice, _ in AuditSeverity.choices}
        if normalized_severity not in valid_severities:
            raise BusinessRuleError("severity invalido para evento de auditoria.")

        if idempotency_key:
            existente = AuditEvent.all_objects.filter(
                empresa=empresa,
                idempotency_key=idempotency_key,
            ).first()
            if existente:
                return existente

        # Bloquea el ultimo evento de la empresa para mantener la cadena hash consistente.
        ultimo = (
            AuditEvent.all_objects.select_for_update()
            .filter(empresa=empresa)
            .only("event_hash")
            .order_by("-occurred_at", "-id")
            .first()
        )
        previous_hash = ultimo.event_hash if ultimo else ""

        evento = AuditEvent(
            empresa=empresa,
            creado_por=usuario,
            module_code=str(module_code).strip().upper(),
            action_code=str(action_code).strip().upper(),
            event_type=str(event_type).strip().upper(),
            severity=normalized_severity,
            entity_type=str(entity_type).strip().upper(),
            entity_id=str(entity_id or "").strip(),
            summary=str(summary or event_type),
            changes=changes or {},
            payload=payload or {},
            meta=meta or {},
            source=str(source or "").strip(),
            request_id=request_id,
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=str(user_agent or "")[:255],
            idempotency_key=idempotency_key,
            previous_hash=previous_hash,
        )
        evento.event_hash = evento.compute_event_hash()

        try:
            evento.save()
            return evento
        except IntegrityError:
            if idempotency_key:
                existente = AuditEvent.all_objects.filter(
                    empresa=empresa,
                    idempotency_key=idempotency_key,
                ).first()
                if existente:
                    return existente
            raise

    @staticmethod
    def consultar_eventos(
        *,
        empresa,
        module_code=None,
        action_code=None,
        event_type=None,
        entity_type=None,
        entity_id=None,
        severity=None,
        created_by_id=None,
        date_from=None,
        date_to=None,
    ):
        """Consulta eventos de auditoria central aplicando filtros operativos."""
        queryset = AuditEvent.all_objects.filter(empresa=empresa)

        if module_code:
            queryset = queryset.filter(module_code=str(module_code).strip().upper())
        if action_code:
            queryset = queryset.filter(action_code=str(action_code).strip().upper())
        if event_type:
            queryset = queryset.filter(event_type=str(event_type).strip().upper())
        if entity_type:
            queryset = queryset.filter(entity_type=str(entity_type).strip().upper())
        if entity_id is not None:
            queryset = queryset.filter(entity_id=str(entity_id).strip())
        if severity:
            queryset = queryset.filter(severity=str(severity).strip().upper())
        if created_by_id:
            queryset = queryset.filter(creado_por_id=created_by_id)
        if date_from:
            queryset = queryset.filter(occurred_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(occurred_at__lte=date_to)

        return queryset.order_by("-occurred_at", "-id")

    @staticmethod
    def verificar_cadena_integridad(*, empresa, limit=5000):
        """Valida la cadena hash de auditoria y retorna resumen de consistencia."""
        eventos = list(
            AuditEvent.all_objects.filter(empresa=empresa)
            .order_by("occurred_at", "id")[:limit]
        )

        previous_hash = ""
        inconsistencias = []

        for evento in eventos:
            expected = evento.compute_event_hash()

            if evento.previous_hash != previous_hash or evento.event_hash != expected:
                inconsistencias.append(str(evento.id))

            previous_hash = evento.event_hash

        return {
            "is_valid": len(inconsistencias) == 0,
            "total_events": len(eventos),
            "inconsistencies": inconsistencias,
        }
