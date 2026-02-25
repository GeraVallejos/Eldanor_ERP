from django.db import models


class Proveedor(models.Model):
    
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

    def __str__(self):
        return self.contacto.nombre