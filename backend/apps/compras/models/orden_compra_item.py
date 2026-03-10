from django.db import models

from apps.compras.models.orden_compra import OrdenCompra
from apps.documentos.models import DocumentoItemBase


class OrdenCompraItem(DocumentoItemBase):

    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name="items"
    )

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ordenes_compra"
    )

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "orden_compra"]),
        ]

    def __str__(self):
        return self.descripcion