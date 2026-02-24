from django.db import models
from apps.core.models.base import BaseModel

class ModelPrueba(BaseModel):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre