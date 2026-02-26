from django.db import models
from apps.core.models import BaseModel
from apps.productos.services.impuesto_validation import clean_impuesto
from apps.core.validators import normalizar_texto


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
        constraints = [
            # Regla 1: No repetir nombre en la misma empresa
            models.UniqueConstraint(
                fields=['empresa', 'nombre'], 
                name='unique_nombre_impuesto_por_empresa'
            ),
            # Regla 2: No repetir porcentaje en la misma empresa
            models.UniqueConstraint(
                fields=['empresa', 'porcentaje'], 
                name='unique_porcentaje_impuesto_por_empresa'
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "nombre"]),
        ]

    def clean(self):
        clean_impuesto(self)

    def save(self, *args, **kwargs):
        self.nombre = normalizar_texto(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje}%)"