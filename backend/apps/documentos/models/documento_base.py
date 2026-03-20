from django.db import models

from apps.core.models import BaseModel


class TipoDocumentoReferencia(models.TextChoices):
    COMPRA_RECEPCION = "COMPRA_RECEPCION", "Recepcion de compra"
    GUIA_RECEPCION = "GUIA_RECEPCION", "Guia de recepcion"
    FACTURA_COMPRA = "FACTURA_COMPRA", "Factura de compra"
    VENTA_FACTURA = "VENTA_FACTURA", "Factura de venta"
    AJUSTE = "AJUSTE", "Ajuste manual"
    TRASLADO = "TRASLADO", "Traslado bodega"
    PRESUPUESTO = "PRESUPUESTO", "Presupuesto"


class EstadoIntegracionTributaria(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_COLA = "EN_COLA", "En cola"
    ENVIADO = "ENVIADO", "Enviado"
    ACEPTADO = "ACEPTADO", "Aceptado"
    RECHAZADO = "RECHAZADO", "Rechazado"


class EstadoContable(models.TextChoices):
    NO_APLICA = "NO_APLICA", "No aplica"
    PENDIENTE = "PENDIENTE", "Pendiente"
    CONTABILIZADO = "CONTABILIZADO", "Contabilizado"
    REVERSADO = "REVERSADO", "Reversado"
    ERROR = "ERROR", "Error"


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
    estado_contable = models.CharField(
        max_length=20,
        choices=EstadoContable.choices,
        default=EstadoContable.NO_APLICA,
    )
    estado_tributario = models.CharField(
        max_length=20,
        choices=EstadoIntegracionTributaria.choices,
        default=EstadoIntegracionTributaria.PENDIENTE,
    )
    track_id_tributario = models.CharField(max_length=120, blank=True)
    mensaje_tributario = models.TextField(blank=True)
    enviado_tributario_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
