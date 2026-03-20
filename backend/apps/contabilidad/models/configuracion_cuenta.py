from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.core.models import BaseModel
from apps.core.validators import normalizar_texto


class ClaveCuentaContable(models.TextChoices):
    CAJA = "CAJA", "Caja"
    BANCO = "BANCO", "Banco"
    CLIENTES = "CLIENTES", "Clientes"
    IVA_CREDITO = "IVA_CREDITO", "IVA credito fiscal"
    PROVEEDORES = "PROVEEDORES", "Proveedores"
    IVA_DEBITO = "IVA_DEBITO", "IVA debito fiscal"
    CAPITAL = "CAPITAL", "Capital"
    VENTAS = "VENTAS", "Ventas"
    COMPRAS = "COMPRAS", "Compras y servicios"


class ConfiguracionCuentaContable(TenantRelationValidationMixin, BaseModel):
    """Parametriza cuentas contables por clave funcional para cada empresa."""

    tenant_fk_fields = ["cuenta"]

    clave = models.CharField(max_length=40, choices=ClaveCuentaContable.choices)
    cuenta = models.ForeignKey(
        "contabilidad.PlanCuenta",
        on_delete=models.PROTECT,
        related_name="configuraciones_funcionales",
    )
    descripcion = models.CharField(max_length=255, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "clave"],
                name="uniq_configuracion_cuenta_contable_empresa_clave",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "clave", "activa"]),
        ]
        ordering = ["clave"]

    def save(self, *args, **kwargs):
        self.descripcion = normalizar_texto(self.descripcion)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.clave} -> {self.cuenta.codigo}"
