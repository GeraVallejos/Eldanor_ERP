from django.db import models


class TipoDireccion(models.TextChoices):
        FACTURACION = "facturacion", "Facturación"
        DESPACHO = "despacho", "Despacho"
        COMERCIAL = "comercial", "Comercial"

class Direccion(models.Model):

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
    pais = models.CharField(max_length=100, default="Chile")

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