from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError

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

    def save(self, *args, **kwargs):
        descuento = Decimal(self.descuento or 0)
        if descuento < 0 or descuento > 100:
            raise ValidationError({"descuento": "El descuento debe estar entre 0 y 100."})

        cantidad = Decimal(self.cantidad or 0)
        precio = Decimal(self.precio_unitario or 0)
        bruto = (cantidad * precio).quantize(Decimal("0.01"))
        neto = (bruto * (Decimal("1") - descuento / Decimal("100"))).quantize(Decimal("0.01"))
        self.subtotal = neto

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"
