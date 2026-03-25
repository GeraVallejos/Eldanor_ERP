from django.db import models

from apps.core.models import BaseModel
from apps.core.validators import normalizar_texto


class Bodega(BaseModel):
    nombre = models.CharField(max_length=150)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre or ""

    def save(self, *args, **kwargs):
        self.nombre = normalizar_texto(self.nombre)
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ["nombre", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nombre"],
                name="unique_bodega_empresa",
            )
        ]
