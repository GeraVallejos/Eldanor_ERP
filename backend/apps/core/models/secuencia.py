from django.db import models
from apps.core.models import BaseModel


class TipoDocumento(models.TextChoices):
    PRESUPUESTO = "PRESUPUESTO", "Presupuesto"
    FACTURA = "FACTURA", "Factura"
    GUIA = "GUIA", "Guía"

class SecuenciaDocumento(BaseModel):

    tipo_documento = models.CharField(max_length=30, choices=TipoDocumento.choices)
    prefijo = models.CharField(
        max_length=10,
        blank=True
    )

    padding = models.PositiveIntegerField(
        default=5
    )
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_documento"],
                name="secuencia_unica_por_empresa_y_tipo"
            )
        ]

    def __str__(self):
        return f"{self.empresa} - {self.tipo_documento}"