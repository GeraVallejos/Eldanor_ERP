from django.db import models

from apps.core.models import BaseModel


class TipoDocumento(models.TextChoices):
    PRESUPUESTO = "PRESUPUESTO", "Presupuesto"
    FACTURA = "FACTURA", "Factura"
    GUIA = "GUIA", "Guia"
    ORDEN_COMPRA = "ORDEN_COMPRA", "Orden de Compra"
    DOCUMENTO_COMPRA = "DOCUMENTO_COMPRA", "Documento de Compra"
    PEDIDO_VENTA = "PEDIDO_VENTA", "Pedido de Venta"
    FACTURA_VENTA = "FACTURA_VENTA", "Factura de Venta"
    GUIA_DESPACHO = "GUIA_DESPACHO", "Guia de Despacho"
    NOTA_CREDITO_VENTA = "NOTA_CREDITO_VENTA", "Nota de Credito Venta"
    ASIENTO_CONTABLE = "ASIENTO_CONTABLE", "Asiento Contable"


class SecuenciaDocumento(BaseModel):
    tipo_documento = models.CharField(max_length=30, choices=TipoDocumento.choices)
    prefijo = models.CharField(max_length=10, blank=True)
    padding = models.PositiveIntegerField(default=5)
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_documento"],
                name="secuencia_unica_por_empresa_y_tipo",
            )
        ]

    def __str__(self):
        return f"{self.empresa} - {self.tipo_documento}"
