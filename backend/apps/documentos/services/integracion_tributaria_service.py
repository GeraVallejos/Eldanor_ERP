from django.utils import timezone

from apps.core.services import DomainEventService, OutboxService
from apps.documentos.models import EstadoIntegracionTributaria


class IntegracionTributariaService:
    """Coordina la preparación de documentos tributarios para emisores externos como SII."""

    @staticmethod
    def solicitar_emision(*, documento, usuario, tipo_documento, payload_extra=None):
        """Marca el documento como listo para integración tributaria y encola el evento de salida."""
        payload = {
            "documento_id": str(documento.id),
            "documento_modelo": documento.__class__.__name__,
            "numero": str(getattr(documento, "numero", "") or ""),
            "empresa_id": str(getattr(documento, "empresa_id", "") or ""),
            "estado_tributario": EstadoIntegracionTributaria.EN_COLA,
            "tipo_documento": tipo_documento,
            "folio_tributario": str(getattr(documento, "folio_tributario", "") or ""),
        }
        if payload_extra:
            payload.update(payload_extra)

        documento.estado_tributario = EstadoIntegracionTributaria.EN_COLA
        documento.mensaje_tributario = ""
        documento.enviado_tributario_en = timezone.now()
        update_fields = ["estado_tributario", "mensaje_tributario", "enviado_tributario_en"]

        if hasattr(documento, "folio_tributario") and not getattr(documento, "folio_tributario", ""):
            documento.folio_tributario = str(getattr(documento, "numero", "") or "")
            update_fields.append("folio_tributario")

        documento.save(update_fields=update_fields)

        dedup_key = f"dte:{documento.__class__.__name__.lower()}:{documento.id}:{tipo_documento}"
        DomainEventService.record_event(
            empresa=documento.empresa,
            aggregate_type=documento.__class__.__name__,
            aggregate_id=documento.id,
            event_type=f"tributario.{tipo_documento.lower()}.solicitado",
            payload=payload,
            meta={"source": "IntegracionTributariaService"},
            idempotency_key=dedup_key,
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=documento.empresa,
            topic="sii.dte",
            event_name=f"{tipo_documento.lower()}.solicitar_emision",
            payload=payload,
            usuario=usuario,
            dedup_key=dedup_key,
        )

