from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models.base import BaseModel
from apps.core.validators import normalizar_texto


class Moneda(BaseModel):
    """Catalogo de monedas habilitadas por empresa para pricing y documentos."""

    codigo = models.CharField(max_length=3)
    nombre = models.CharField(max_length=80)
    simbolo = models.CharField(max_length=10, blank=True)
    decimales = models.PositiveSmallIntegerField(default=2)
    tasa_referencia = models.DecimalField(max_digits=18, decimal_places=6, default=1)
    es_base = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="unique_moneda_codigo_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "codigo"]),
            models.Index(fields=["empresa", "activa"]),
        ]
        ordering = ["codigo"]

    def clean(self):
        super().clean()

        self.codigo = str(self.codigo or "").strip().upper()
        self.nombre = normalizar_texto(self.nombre)
        self.simbolo = str(self.simbolo or "").strip()

        if len(self.codigo) != 3 or not self.codigo.isalpha():
            raise ValidationError({"codigo": "El codigo de moneda debe tener 3 letras."})

        if self.decimales > 6:
            raise ValidationError({"decimales": "La moneda no puede manejar mas de 6 decimales."})

        if Decimal(self.tasa_referencia or 0) <= 0:
            raise ValidationError({"tasa_referencia": "La tasa de referencia debe ser mayor a cero."})

        if self.es_base:
            self.tasa_referencia = Decimal("1")

        if self.es_base and not self.activa:
            raise ValidationError({"activa": "La moneda base no puede estar inactiva."})

    def save(self, *args, **kwargs):
        self.codigo = str(self.codigo or "").strip().upper()
        self.nombre = normalizar_texto(self.nombre)
        self.simbolo = str(self.simbolo or "").strip()

        if self.es_base:
            self.tasa_referencia = Decimal("1")
            if self.empresa_id:
                self.__class__.all_objects.filter(
                    empresa_id=self.empresa_id,
                    es_base=True,
                ).exclude(pk=self.pk).update(es_base=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"