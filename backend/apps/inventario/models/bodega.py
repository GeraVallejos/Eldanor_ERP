from django.db import models
from apps.core.models import BaseModel

class Bodega(BaseModel):

    nombre = models.CharField(max_length=150)

    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nombre"],
                name="unique_bodega_empresa"
            )
        ]