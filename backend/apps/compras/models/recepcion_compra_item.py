from django.db import models
from apps.core.models import BaseModel
from apps.productos.models import Producto
from apps.compras.models import RecepcionCompra, OrdenCompraItem


class RecepcionCompraItem(BaseModel):

    recepcion = models.ForeignKey(
        RecepcionCompra,
        on_delete=models.CASCADE,
        related_name="items"
    )

    orden_item = models.ForeignKey(
        OrdenCompraItem,
        on_delete=models.SET_NULL,
        related_name="recepciones",
        null=True,
        blank=True,
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    precio_unitario = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "recepcion"]),
        ]