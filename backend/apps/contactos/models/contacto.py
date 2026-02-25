from django.db import models
from apps.core.models import BaseModel
from apps.core.validators import formatear_rut, validar_rut


class Tipo(models.TextChoices):
        PERSONA = "persona", "Persona"
        EMPRESA = "empresa", "Empresa"

class Contacto(BaseModel):

    nombre = models.CharField(max_length=255, db_index=True)
    razon_social = models.CharField(max_length=255, blank=True, null=True)

    rut = models.CharField(
        max_length=12,
        db_index=True,
        blank=True,
        null=True
    )

    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PERSONA)

    # contacto
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    celular = models.CharField(max_length=50, blank=True, null=True)

    activo = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "nombre"]),
            models.Index(fields=["empresa", "activo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "rut"],
                name="unique_contacto_rut_empresa"
            )
        ]
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        if self.rut:
            self.rut = formatear_rut(self.rut)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean() 

        if self.rut:
            self.rut = formatear_rut(self.rut)
            validar_rut(self.rut)