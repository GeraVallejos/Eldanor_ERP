from django.db import models

from apps.contactos.models import Proveedor
from apps.documentos.models import DocumentoTributableBase


class EstadoOrdenCompra(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ENVIADA = "ENVIADA", "Enviada"
    PARCIAL = "PARCIAL", "Parcialmente recibida"
    RECIBIDA = "RECIBIDA", "Recibida"
    CANCELADA = "CANCELADA", "Cancelada"


class OrdenCompra(DocumentoTributableBase):

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="ordenes_compra"
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoOrdenCompra.choices,
        default=EstadoOrdenCompra.BORRADOR
    )

    fecha_emision = models.DateField()

    fecha_entrega = models.DateField(
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="unique_numero_oc_por_empresa"
            )
        ]

        indexes = [
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "proveedor"]),
        ]

    def __str__(self):
        return f"OC {self.numero}"