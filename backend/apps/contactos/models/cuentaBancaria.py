from django.db import models
from apps.core.validators import formatear_rut, validar_rut


class TipoCuenta(models.TextChoices):
        CORRIENTE = "corriente", "Cuenta Corriente"
        VISTA = "vista", "Cuenta Vista"
        AHORRO = "ahorro", "Cuenta de Ahorro"

class CuentaBancaria(models.Model):

    contacto = models.ForeignKey(
        "contactos.Contacto",
        on_delete=models.CASCADE,
        related_name="cuentas_bancarias"
    )

    banco = models.CharField(max_length=100)
    tipo_cuenta = models.CharField(
        max_length=20,
        choices=TipoCuenta.choices
    )
    numero_cuenta = models.CharField(max_length=50)
    titular = models.CharField(max_length=255)
    rut_titular = models.CharField(max_length=12)

    activa = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["contacto", "activa"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["contacto", "numero_cuenta"],
                name="unique_cuenta_por_contacto"
            )
        ]

    def clean(self):
        if self.rut_titular:
            self.rut_titular = formatear_rut(self.rut_titular)
            validar_rut(self.rut_titular)