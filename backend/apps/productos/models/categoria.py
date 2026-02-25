from django.db import models
from apps.core.models import BaseModel


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
        # Normalizamos el nombre: "electrónica" -> "Electrónica"
        if self.nombre:
            self.nombre = self.nombre.strip().title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre