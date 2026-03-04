from django.db import models
from apps.core.models import BaseModel


class TipoDocumento(models.TextChoices):
    PRESUPUESTO = "PRESUPUESTO", "Presupuesto"
    FACTURA = "FACTURA", "Factura"
    GUIA = "GUIA", "Guía"

class SecuenciaDocumento(BaseModel):

    tipo_documento = models.CharField(max_length=30, choices=TipoDocumento.choices)
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("empresa", "tipo_documento")

    def __str__(self):
        return f"{self.empresa} - {self.tipo_documento}"