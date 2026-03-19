from django.utils import timezone

from apps.core.services.domain_event_service import DomainEventService
from apps.core.services.outbox_service import OutboxService
from apps.documentos.models import EstadoIntegracionTributaria
from apps.documentos.services.folio_tributario_service import FolioTributarioService


class IntegracionTributariaService:
    """Coordina la preparacion de documentos tributarios para emisores externos como SII."""

    @staticmethod
    def solicitar_emision(*, documento, usuario, tipo_documento, payload_extra=None):
        """Marca el documento como listo para integracion tributaria y encola el evento de salida."""
        tipo_normalizado = FolioTributarioService.normalizar_tipo_documento(
            tipo_documento=tipo_documento,
        )
        config = FolioTributarioService.obtener_configuracion_activa(empresa=documento.empresa)

        if hasattr(documento, "folio_tributario") and getattr(documento, "folio_tributario", ""):
            folio_tributario = str(documento.folio_tributario)
            rango = None
        else:
            rango, folio_tributario = FolioTributarioService.reservar_siguiente_folio(
                empresa=documento.empresa,
                tipo_documento=tipo_normalizado,
            )

        payload = {
            "documento_id": str(documento.id),
            "documento_modelo": documento.__class__.__name__,
            "numero": str(getattr(documento, "numero", "") or ""),
            "empresa_id": str(getattr(documento, "empresa_id", "") or ""),
            "estado_tributario": EstadoIntegracionTributaria.EN_COLA,
            "tipo_documento": tipo_documento,
            "folio_tributario": folio_tributario,
            "ambiente": config.ambiente,
            "rut_emisor": config.rut_emisor,
            "resolucion_numero": config.resolucion_numero,
            "rango_folio_id": str(rango.id) if rango else None,
        }
        if payload_extra:
            payload.update(payload_extra)

        documento.estado_tributario = EstadoIntegracionTributaria.EN_COLA
        documento.mensaje_tributario = ""
        documento.enviado_tributario_en = timezone.now()
        update_fields = ["estado_tributario", "mensaje_tributario", "enviado_tributario_en"]

        if hasattr(documento, "folio_tributario"):
            documento.folio_tributario = folio_tributario
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
