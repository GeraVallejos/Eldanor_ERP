from django.db import models

from apps.core.models import BaseModel
from apps.productos.models import Producto


class DocumentoCompraProveedorItem(BaseModel):

    documento = models.ForeignKey(
        "compras.DocumentoCompraProveedor",
        on_delete=models.CASCADE,
        related_name="items",
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
    )

    descripcion = models.CharField(max_length=255, blank=True)

    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=2)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    recepcion_item = models.ForeignKey(
        "compras.RecepcionCompraItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documento_items",
    )

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "documento"]),
        ]

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"
