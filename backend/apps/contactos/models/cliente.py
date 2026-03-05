from django.db import models
from apps.core.validators import normalizar_texto
from apps.core.models.base import BaseModel
from django.core.exceptions import ValidationError
from apps.core.mixins import TenantRelationValidationMixin


class Cliente(TenantRelationValidationMixin, BaseModel):

    tenant_fk_fields = ["contacto"]

    contacto = models.OneToOneField(
        "contactos.Contacto",
        on_delete=models.CASCADE,
        related_name="cliente"
    )
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dias_credito = models.PositiveIntegerField(default=0)

    categoria_cliente = models.CharField(max_length=50, blank=True, null=True)
    segmento = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['contacto__nombre']

    def save(self, *args, **kwargs):
        self.categoria_cliente = normalizar_texto(self.categoria_cliente)
        self.segmento = normalizar_texto(self.segmento)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.contacto.nombre
