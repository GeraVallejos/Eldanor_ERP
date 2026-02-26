import uuid
from django.db import models
from apps.core.validators import formatear_rut, normalizar_texto, validar_rut


class TipoCuenta(models.TextChoices):
        CORRIENTE = "CORRIENTE", "Cuenta Corriente"
        VISTA = "VISTA", "Cuenta Vista"
        AHORRO = "AHORRO", "Cuenta de Ahorro"

class CuentaBancaria(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    def save(self, *args, **kwargs):

        self.banco = normalizar_texto(self.banco)
        self.titular = normalizar_texto(self.titular)
        # El número de cuenta no se pasa a mayúsculas (por si tiene letras), 
        # pero sí se limpia de espacios
        self.numero_cuenta = self.numero_cuenta.strip() if self.numero_cuenta else None
        if self.rut_titular:
            from apps.core.validators import formatear_rut
            self.rut_titular = formatear_rut(self.rut_titular)
        super().save(*args, **kwargs)