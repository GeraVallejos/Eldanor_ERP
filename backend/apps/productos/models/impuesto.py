from django.db import models
from apps.core.models import BaseModel
from apps.productos.services.impuesto_validation import clean_impuesto


class Impuesto(BaseModel):
    nombre = models.CharField(max_length=100)

    porcentaje = models.DecimalField(
        default=19,
        max_digits=5,
        decimal_places=2,
        help_text="Porcentaje de impuesto (ej: 19.00)"
    )

    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("empresa", "nombre")
        unique_together = ("empresa", "porcentaje")
        indexes = [
            models.Index(fields=["empresa", "nombre"]),
        ]

    def clean(self):
        clean_impuesto(self)

    def save(self, *args, **kwargs):
        # Normalizamos el nombre: "electrónica" -> "Electrónica"
        if self.nombre:
            self.nombre = self.nombre.strip().capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje}%)"