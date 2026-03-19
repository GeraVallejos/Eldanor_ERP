from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.core.models import BaseModel
from apps.core.validators import normalizar_texto


class EstadoAsientoContable(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONTABILIZADO = "CONTABILIZADO", "Contabilizado"
    ANULADO = "ANULADO", "Anulado"


class OrigenAsientoContable(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    INTEGRACION = "INTEGRACION", "Integracion"


class AsientoContable(BaseModel):
    """Cabecera contable para diarios manuales o integraciones de negocio."""

    numero = models.CharField(max_length=50)
    fecha = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoAsientoContable.choices,
        default=EstadoAsientoContable.BORRADOR,
    )
    origen = models.CharField(
        max_length=20,
        choices=OrigenAsientoContable.choices,
        default=OrigenAsientoContable.MANUAL,
    )
    glosa = models.CharField(max_length=255)
    referencia_tipo = models.CharField(max_length=80, blank=True)
    referencia_id = models.UUIDField(null=True, blank=True)
    total_debe = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_haber = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cuadrado = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="uniq_asiento_contable_empresa_numero",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "estado", "fecha"]),
            models.Index(fields=["empresa", "origen", "fecha"]),
        ]
        ordering = ["-fecha", "-creado_en"]

    def clean(self):
        super().clean()
        self.glosa = normalizar_texto(self.glosa)
        self.referencia_tipo = normalizar_texto(self.referencia_tipo)
        if Decimal(self.total_debe or 0) < 0 or Decimal(self.total_haber or 0) < 0:
            raise ValidationError("Los totales del asiento no pueden ser negativos.")

    def save(self, *args, **kwargs):
        self.glosa = normalizar_texto(self.glosa)
        self.referencia_tipo = normalizar_texto(self.referencia_tipo)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero} - {self.glosa}"


class MovimientoContable(TenantRelationValidationMixin, BaseModel):
    """Linea contable que afecta una cuenta del plan."""

    tenant_fk_fields = ["asiento", "cuenta"]

    asiento = models.ForeignKey(
        "contabilidad.AsientoContable",
        on_delete=models.CASCADE,
        related_name="movimientos",
    )
    cuenta = models.ForeignKey(
        "contabilidad.PlanCuenta",
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    glosa = models.CharField(max_length=255, blank=True)
    debe = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    haber = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "asiento"]),
            models.Index(fields=["empresa", "cuenta"]),
        ]
        ordering = ["creado_en", "id"]

    def clean(self):
        super().clean()
        self.glosa = normalizar_texto(self.glosa)

        debe = Decimal(self.debe or 0)
        haber = Decimal(self.haber or 0)
        if debe < 0 or haber < 0:
            raise ValidationError("Debe y haber no pueden ser negativos.")
        if (debe == 0 and haber == 0) or (debe > 0 and haber > 0):
            raise ValidationError("Cada linea debe informar solo debe o solo haber.")
        if self.cuenta and not self.cuenta.acepta_movimientos:
            raise ValidationError({"cuenta": "La cuenta seleccionada no acepta movimientos directos."})
        if self.cuenta and not self.cuenta.activa:
            raise ValidationError({"cuenta": "La cuenta seleccionada esta inactiva."})

    def save(self, *args, **kwargs):
        self.glosa = normalizar_texto(self.glosa)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cuenta} D:{self.debe} H:{self.haber}"
