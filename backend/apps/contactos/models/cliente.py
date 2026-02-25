from django.db import models


class Cliente(models.Model):
   
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

    def __str__(self):
        return self.contacto.nombre
