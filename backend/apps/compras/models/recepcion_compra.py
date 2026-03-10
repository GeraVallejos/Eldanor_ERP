from django.db import models
from apps.core.models import BaseModel
from apps.compras.models.orden_compra import OrdenCompra


class EstadoRecepcion(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADA = "CONFIRMADA", "Confirmada"


class RecepcionCompra(BaseModel):

    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.PROTECT,
        related_name="recepciones"
    )

    fecha = models.DateField()

    estado = models.CharField(
        max_length=20,
        choices=EstadoRecepcion.choices,
        default=EstadoRecepcion.BORRADOR
    )

    observaciones = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "orden_compra"]),
        ]

    def __str__(self):
        return f"Recepción {self.id}"