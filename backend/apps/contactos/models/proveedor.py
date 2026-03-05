from django.db import models
from apps.core.validators import normalizar_texto
from apps.core.models.base import BaseModel
from apps.core.mixins import TenantRelationValidationMixin


class Proveedor(TenantRelationValidationMixin, BaseModel):

    tenant_fk_fields = ["contacto"]
    
    contacto = models.OneToOneField(
        "contactos.Contacto",
        on_delete=models.CASCADE,
        related_name="proveedor"
    )

    giro = models.CharField(max_length=255, blank=True, null=True)
    vendedor_contacto = models.CharField(max_length=255, blank=True, null=True)

    dias_credito = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['contacto__nombre']


    def save(self, *args, **kwargs):
        self.giro = normalizar_texto(self.giro)
        self.vendedor_contacto = normalizar_texto(self.vendedor_contacto)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.contacto.nombre