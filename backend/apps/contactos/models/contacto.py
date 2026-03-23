from django.db import models
from apps.core.models import BaseModel
from apps.core.validators import formatear_rut, normalizar_texto, validar_rut_con_dv
from django.core.exceptions import ValidationError


class TipoContacto(models.TextChoices):
        PERSONA = "PERSONA", "Persona Natural"
        EMPRESA = "EMPRESA", "Empresa"

class Contacto(BaseModel):

    nombre = models.CharField(max_length=255, db_index=True)
    razon_social = models.CharField(max_length=255, blank=True, null=True)

    rut = models.CharField(
        max_length=12,
        db_index=True,
        blank=False,
        null=False,
    )

    tipo = models.CharField(max_length=20, choices=TipoContacto.choices, default=TipoContacto.PERSONA, null=False, blank=False  )

    # contacto
    email = models.EmailField(blank=False, null=False)
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
            ),
            models.CheckConstraint(
                condition=~models.Q(rut=""),
                name="check_contacto_rut_not_empty",
            ),
            models.CheckConstraint(
                condition=~models.Q(email=""),
                name="check_contacto_email_not_empty",
            ),
            models.CheckConstraint(
                condition=~models.Q(tipo=""),
                name="check_contacto_tipo_not_empty",
            ),
        ]
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        self.nombre = normalizar_texto(self.nombre)
        self.razon_social = normalizar_texto(self.razon_social)
        self.email = normalizar_texto(self.email, es_email=True)
        if self.rut:
            self.rut = formatear_rut(self.rut)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        errors = {}

        if not str(self.rut or "").strip():
            errors["rut"] = "Este campo es obligatorio."

        if not str(self.email or "").strip():
            errors["email"] = "Este campo es obligatorio."

        if not str(self.tipo or "").strip():
            errors["tipo"] = "Este campo es obligatorio."

        if self.rut:
            self.rut = formatear_rut(self.rut)
            validar_rut_con_dv(self.rut)

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        # Si el RUT existe, lo mostramos, si no, solo el nombre
        if self.rut:
            return f"{self.nombre} ({self.rut})"
        return self.nombre
