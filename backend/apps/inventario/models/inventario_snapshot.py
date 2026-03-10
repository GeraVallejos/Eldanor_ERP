from django.db import models

from apps.core.models import BaseModel


class InventorySnapshot(BaseModel):
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="snapshots_inventario",
    )
    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.CASCADE,
        related_name="snapshots_inventario",
    )
    movimiento = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapshots",
    )

    stock = models.DecimalField(max_digits=12, decimal_places=2)
    costo_promedio = models.DecimalField(max_digits=12, decimal_places=4)
    valor_stock = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["empresa", "producto", "bodega", "creado_en"]),
            models.Index(fields=["empresa", "creado_en"]),
        ]
