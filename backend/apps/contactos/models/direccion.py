import uuid
from django.db import models
from apps.core.validators import normalizar_texto


class TipoDireccion(models.TextChoices):
        FACTURACION = "FACTURACION", "Facturación"
        DESPACHO = "DESPACHO", "Despacho"
        COMERCIAL = "COMERCIAL", "Comercial"

class Direccion(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contacto = models.ForeignKey(
        "contactos.Contacto",
        on_delete=models.CASCADE,
        related_name="direcciones"
    )

    tipo = models.CharField(max_length=20, choices=TipoDireccion.choices)

    direccion = models.TextField()
    comuna = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, null=True)
    pais = models.CharField(max_length=100, default="CHILE")

    class Meta:
        indexes = [
            models.Index(fields=["contacto", "tipo"]),
        ]
        constraints = [
        models.UniqueConstraint(
            fields=["contacto", "tipo"],
            name="unique_tipo_direccion_por_contacto"
        )
    ]
        
    def save(self, *args, **kwargs):
        self.direccion = normalizar_texto(self.direccion)
        self.comuna = normalizar_texto(self.comuna)
        self.ciudad = normalizar_texto(self.ciudad)
        self.pais = normalizar_texto(self.pais)
        super().save(*args, **kwargs)