from django.db import models

from apps.core.models import BaseModel


class StockLote(BaseModel):
    """Stock disponible por lote para trazabilidad y vencimientos."""

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="stocks_lote",
    )
    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.CASCADE,
        related_name="stocks_lote",
    )
    lote_codigo = models.CharField(max_length=80)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "producto", "bodega", "lote_codigo"],
                name="uniq_stock_lote_empresa_producto_bodega",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "producto", "bodega"]),
            models.Index(fields=["empresa", "lote_codigo"]),
        ]
