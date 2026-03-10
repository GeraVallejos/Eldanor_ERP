from django.db import transaction
from django.db.models import F
from apps.core.models import SecuenciaDocumento


class SecuenciaService:

    @staticmethod
    @transaction.atomic
    def obtener_siguiente_numero(empresa, tipo_documento):

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