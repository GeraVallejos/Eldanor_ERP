from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import Empresa, Moneda
from apps.core.models.secuencia import SecuenciaDocumento, TipoDocumento


@receiver(post_save, sender=Empresa)
def crear_secuencias_empresa(sender, instance, created, **kwargs):

    if not created:
        return

    tipos_documento = [
        TipoDocumento.PRESUPUESTO,
        TipoDocumento.ORDEN_COMPRA,
        TipoDocumento.DOCUMENTO_COMPRA,
        TipoDocumento.PEDIDO_VENTA,
        TipoDocumento.FACTURA_VENTA,
        TipoDocumento.GUIA_DESPACHO,
        TipoDocumento.NOTA_CREDITO_VENTA,
    ]

    for tipo in tipos_documento:
        SecuenciaDocumento.all_objects.get_or_create(
            empresa=instance,
            tipo_documento=tipo,
            defaults={"ultimo_numero": 0}
        )

    Moneda.all_objects.get_or_create(
        empresa=instance,
        codigo="CLP",
        defaults={
            "nombre": "Peso Chileno",
            "simbolo": "$",
            "decimales": 2,
            "tasa_referencia": 1,
            "es_base": True,
            "activa": True,
        },
    )
    Moneda.all_objects.get_or_create(
        empresa=instance,
        codigo="USD",
        defaults={
            "nombre": "Dolar Estadounidense",
            "simbolo": "US$",
            "decimales": 2,
            "tasa_referencia": 950,
            "es_base": False,
            "activa": True,
        },
    )