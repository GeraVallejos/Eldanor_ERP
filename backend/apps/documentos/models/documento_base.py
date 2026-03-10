from django.db import models

from apps.core.models import BaseModel


class TipoDocumentoReferencia(models.TextChoices):
    COMPRA_RECEPCION = "COMPRA_RECEPCION", "Recepcion de compra"
    VENTA_FACTURA = "VENTA_FACTURA", "Factura de venta"
    AJUSTE = "AJUSTE", "Ajuste manual"
    TRASLADO = "TRASLADO", "Traslado bodega"
    PRESUPUESTO = "PRESUPUESTO", "Presupuesto"


class DocumentoReferenciaMixin(models.Model):
    documento_tipo = models.CharField(
        max_length=50,
        choices=TipoDocumentoReferencia.choices,
        null=True,
        blank=True,
    )
    documento_id = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True


class DocumentoBase(BaseModel):
    estado = models.CharField(max_length=20)
    observaciones = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        abstract = True


class DocumentoNumeradoBase(DocumentoBase):
    numero = models.CharField(max_length=50)

    class Meta:
        abstract = True


class DocumentoTributableBase(DocumentoNumeradoBase):
    impuestos = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        abstract = True