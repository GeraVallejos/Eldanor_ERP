from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.core.models import BaseModel
from apps.core.validators import normalizar_texto


class TipoCuentaContable(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    PASIVO = "PASIVO", "Pasivo"
    PATRIMONIO = "PATRIMONIO", "Patrimonio"
    INGRESO = "INGRESO", "Ingreso"
    GASTO = "GASTO", "Gasto"


class PlanCuenta(TenantRelationValidationMixin, BaseModel):
    """Cuenta contable del plan de cuentas por empresa."""

    tenant_fk_fields = ["padre"]

    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TipoCuentaContable.choices)
    padre = models.ForeignKey(
        "contabilidad.PlanCuenta",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="hijas",
    )
    acepta_movimientos = models.BooleanField(default=True)
    activa = models.BooleanField(default=True)
    descripcion = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="uniq_plan_cuenta_empresa_codigo",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "tipo", "activa"]),
            models.Index(fields=["empresa", "codigo"]),
        ]
        ordering = ["codigo"]

    def clean(self):
        super().clean()
        self.codigo = str(self.codigo or "").strip().upper()
        self.nombre = normalizar_texto(self.nombre)
        self.descripcion = normalizar_texto(self.descripcion)

        if not self.codigo:
            raise ValidationError({"codigo": "El codigo de cuenta es obligatorio."})
        if self.padre_id and self.padre_id == self.id:
            raise ValidationError({"padre": "La cuenta no puede ser su propio padre."})
        if self.padre and self.padre.acepta_movimientos:
            raise ValidationError({"padre": "La cuenta padre no debe aceptar movimientos directos."})

    def save(self, *args, **kwargs):
        self.codigo = str(self.codigo or "").strip().upper()
        self.nombre = normalizar_texto(self.nombre)
        self.descripcion = normalizar_texto(self.descripcion)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
