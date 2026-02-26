from django.db import models
from apps.core.models import BaseModel
from apps.core.validators import normalizar_texto


class Categoria(BaseModel):
    nombre = models.CharField(max_length=150)

    descripcion = models.TextField(blank=True)

    activa = models.BooleanField(default=True)

    class Meta:
        unique_together = ("empresa", "nombre")
        indexes = [
            models.Index(fields=["empresa", "nombre"]),
        ]

    def save(self, *args, **kwargs):
        self.nombre = normalizar_texto(self.nombre)
        self.descripcion = normalizar_texto(self.descripcion)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre