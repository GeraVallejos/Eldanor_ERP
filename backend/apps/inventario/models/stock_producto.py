from django.db import models
from apps.core.models.base import BaseModel


class StockProducto(BaseModel):
    
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="stocks"
    )

    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.CASCADE,
        related_name="stocks"
    )

    stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    valor_stock = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "producto", "bodega"],
                name="unique_producto_bodega"
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "producto"]),
        ]