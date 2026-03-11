from decimal import Decimal

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

    def save(self, *args, **kwargs):
        cantidad = Decimal(self.cantidad or 0)
        precio = Decimal(self.precio_unitario or 0)
        subtotal = (cantidad * precio).quantize(Decimal("0.01"))

        tasa = Decimal("0")
        if self.impuesto_id and getattr(self.impuesto, "porcentaje", None) is not None:
            tasa = Decimal(self.impuesto.porcentaje)

        impuesto_monto = (subtotal * tasa / Decimal("100")).quantize(Decimal("0.01"))
        self.subtotal = subtotal
        self.total = (subtotal + impuesto_monto).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.descripcion