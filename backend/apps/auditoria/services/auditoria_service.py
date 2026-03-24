from django.db import IntegrityError, transaction
from django.db.models import Q

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
    def consultar_eventos_por_entidades(
        *,
        empresa,
        entities,
        limit=None,
    ):
        """Consulta eventos de auditoria para multiples entidades relacionadas en una sola operacion."""
        queryset = AuditEvent.all_objects.filter(empresa=empresa)

        normalized_entities = [
            (
                str(entity_type or "").strip().upper(),
                str(entity_id or "").strip(),
            )
            for entity_type, entity_id in (entities or [])
            if str(entity_type or "").strip() and str(entity_id or "").strip()
        ]

        if not normalized_entities:
            return queryset.none()

        entity_filter = Q()
        for entity_type, entity_id in normalized_entities:
            entity_filter |= Q(entity_type=entity_type, entity_id=entity_id)

        queryset = queryset.filter(entity_filter).order_by("-occurred_at", "-id")

        if limit is None:
            return queryset

        try:
            normalized_limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise BusinessRuleError("limit debe ser un entero positivo.") from exc

        if normalized_limit <= 0:
            raise BusinessRuleError("limit debe ser mayor que cero.")

        return queryset[:normalized_limit]

    @staticmethod
    def verificar_cadena_integridad(*, empresa, limit=None):
        return AuditoriaService.verificar_cadena_integridad_avanzada(
            empresa=empresa,
            limit=limit,
            date_from=None,
            date_to=None,
            include_blocks=False,
            block_size=1000,
        )

    @staticmethod
    def verificar_cadena_integridad_avanzada(
        *,
        empresa,
        limit=None,
        date_from=None,
        date_to=None,
        include_blocks=False,
        block_size=1000,
    ):
        """Valida cadena hash con soporte de rango y resumen por bloques.

        - Sin filtros revisa toda la cadena de la empresa.
        - Con date_from/date_to valida solo ese rango, anclando el hash previo
          al evento inmediatamente anterior del rango.
        """
        queryset = AuditEvent.all_objects.filter(empresa=empresa)
        if date_from:
            queryset = queryset.filter(occurred_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(occurred_at__lte=date_to)
        queryset = queryset.order_by("occurred_at", "id")

        normalized_limit = None
        if limit is not None:
            try:
                normalized_limit = int(limit)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleError("limit debe ser un entero positivo.") from exc

            if normalized_limit <= 0:
                raise BusinessRuleError("limit debe ser mayor que cero.")

            queryset = queryset[:normalized_limit]

        normalized_block_size = 1000
        if include_blocks:
            try:
                normalized_block_size = int(block_size)
            except (TypeError, ValueError) as exc:
                raise BusinessRuleError("block_size debe ser un entero positivo.") from exc

            if normalized_block_size <= 0:
                raise BusinessRuleError("block_size debe ser mayor que cero.")

        first_event = queryset.first()
        if first_event is None:
            return {
                "is_valid": True,
                "total_events": 0,
                "inconsistencies": [],
                "is_partial_scan": normalized_limit is not None,
                "has_range_filter": bool(date_from or date_to),
                "blocks": [],
            }

        previous_hash = ""
        if date_from is not None or date_to is not None:
            previous_event = (
                AuditEvent.all_objects.filter(empresa=empresa)
                .filter(
                    Q(occurred_at__lt=first_event.occurred_at)
                    | Q(occurred_at=first_event.occurred_at, id__lt=first_event.id)
                )
                .only("event_hash")
                .order_by("-occurred_at", "-id")
                .first()
            )
            previous_hash = previous_event.event_hash if previous_event else ""

        inconsistencias = []
        total_events = 0
        blocks = []
        block_cursor = {
            "index": 1,
            "count": 0,
            "from_event_id": None,
            "to_event_id": None,
            "from_occurred_at": None,
            "to_occurred_at": None,
            "inconsistency_ids": [],
        }

        def _flush_block():
            if block_cursor["count"] == 0:
                return
            blocks.append(
                {
                    "index": block_cursor["index"],
                    "from_event_id": block_cursor["from_event_id"],
                    "to_event_id": block_cursor["to_event_id"],
                    "from_occurred_at": block_cursor["from_occurred_at"],
                    "to_occurred_at": block_cursor["to_occurred_at"],
                    "total_events": block_cursor["count"],
                    "inconsistency_count": len(block_cursor["inconsistency_ids"]),
                    "is_valid": len(block_cursor["inconsistency_ids"]) == 0,
                    "inconsistency_ids": list(block_cursor["inconsistency_ids"]),
                }
            )
            block_cursor["index"] += 1
            block_cursor["count"] = 0
            block_cursor["from_event_id"] = None
            block_cursor["to_event_id"] = None
            block_cursor["from_occurred_at"] = None
            block_cursor["to_occurred_at"] = None
            block_cursor["inconsistency_ids"] = []

        for evento in queryset.iterator(chunk_size=1000):
            total_events += 1
            if include_blocks and block_cursor["count"] == 0:
                block_cursor["from_event_id"] = str(evento.id)
                block_cursor["from_occurred_at"] = evento.occurred_at.isoformat()

            if include_blocks:
                block_cursor["count"] += 1
                block_cursor["to_event_id"] = str(evento.id)
                block_cursor["to_occurred_at"] = evento.occurred_at.isoformat()

            expected = evento.compute_event_hash()

            if evento.previous_hash != previous_hash or evento.event_hash != expected:
                inconsistency_id = str(evento.id)
                inconsistencias.append(inconsistency_id)
                if include_blocks:
                    block_cursor["inconsistency_ids"].append(inconsistency_id)

            previous_hash = evento.event_hash

            if include_blocks and block_cursor["count"] >= normalized_block_size:
                _flush_block()

        if include_blocks:
            _flush_block()

        return {
            "is_valid": len(inconsistencias) == 0,
            "total_events": total_events,
            "inconsistencies": inconsistencias,
            "is_partial_scan": normalized_limit is not None,
            "has_range_filter": bool(date_from or date_to),
            "blocks": blocks,
        }
