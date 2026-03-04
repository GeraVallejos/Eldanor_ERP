from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import Empresa
from apps.core.models.secuencia import SecuenciaDocumento


@receiver(post_save, sender=Empresa)
def crear_secuencias_empresa(sender, instance, created, **kwargs):

    if not created:
        return

    tipos_documento = [
        "PRESUPUESTO",
        # En el futuro:
        # "FACTURA",
        # "GUIA",
    ]

    for tipo in tipos_documento:
        SecuenciaDocumento.all_objects.create(
            empresa=instance,
            tipo_documento=tipo,
            ultimo_numero=0
        )