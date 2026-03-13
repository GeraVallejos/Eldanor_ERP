from django.db import transaction
from apps.core.models import SecuenciaDocumento


class SecuenciaService:

    @staticmethod
    def obtener_numero_siguiente_disponible(empresa, tipo_documento):
        """Calcula el siguiente folio sin persistir el incremento."""

        secuencia, _ = (
            SecuenciaDocumento.all_objects
            .get_or_create(
                empresa=empresa,
                tipo_documento=tipo_documento,
                defaults={
                    "ultimo_numero": 0,
                    "prefijo": tipo_documento[:3],
                    "padding": 5,
                },
            )
        )

        numero = str(secuencia.ultimo_numero + 1).zfill(secuencia.padding)

        if secuencia.prefijo:
            return f"{secuencia.prefijo}-{numero}"

        return numero

    @staticmethod
    @transaction.atomic
    def obtener_siguiente_numero(empresa, tipo_documento):
        """Reserva y retorna el siguiente folio de forma atomica."""

        secuencia, _ = (
            SecuenciaDocumento.all_objects
            .select_for_update()
            .get_or_create(
                empresa=empresa,
                tipo_documento=tipo_documento,
                defaults={
                    "ultimo_numero": 0,
                    "prefijo": tipo_documento[:3],
                    "padding": 5
                }
            )
        )

        secuencia.ultimo_numero += 1
        secuencia.save(update_fields=["ultimo_numero"])

        numero = str(secuencia.ultimo_numero).zfill(secuencia.padding)

        if secuencia.prefijo:
            return f"{secuencia.prefijo}-{numero}"

        return numero