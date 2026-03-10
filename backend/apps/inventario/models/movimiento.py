from django.db import models
from apps.core.models import BaseModel
from apps.documentos.models import DocumentoReferenciaMixin, TipoDocumentoReferencia

class TipoMovimiento(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SALIDA = "SALIDA", "Salida"

class MovimientoInventario(DocumentoReferenciaMixin, BaseModel):

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="movimientos"
    )

    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.PROTECT,
        related_name="movimientos"
    )

    tipo = models.CharField(
        max_length=10,
        choices=TipoMovimiento.choices
    )

    cantidad = models.DecimalField(max_digits=12, decimal_places=2)

    stock_anterior = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False
    )

    stock_nuevo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False
    )

    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4)

    valor_total = models.DecimalField(max_digits=14, decimal_places=2)

    documento_tipo = models.CharField(
        max_length=50,
        choices=TipoDocumentoReferencia.choices,
        null=True,
        blank=True
    )

    referencia = models.CharField(max_length=150)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["empresa", "producto"]),
            models.Index(fields=["empresa", "producto", "bodega"]),
            models.Index(fields=["empresa", "documento_tipo"]),
            models.Index(fields=["empresa", "creado_en"])
        ]