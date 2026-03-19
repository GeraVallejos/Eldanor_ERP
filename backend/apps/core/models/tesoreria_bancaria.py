from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.core.models.base import BaseModel
from apps.core.validators import normalizar_texto
from apps.documentos.models import EstadoContable


class TipoCuentaBancoEmpresa(models.TextChoices):
    CORRIENTE = "CORRIENTE", "Cuenta corriente"
    VISTA = "VISTA", "Cuenta vista"
    AHORRO = "AHORRO", "Cuenta de ahorro"


class TipoMovimientoBancario(models.TextChoices):
    CREDITO = "CREDITO", "Credito"
    DEBITO = "DEBITO", "Debito"


class OrigenMovimientoBancario(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    IMPORTACION = "IMPORTACION", "Importacion"
    CONCILIACION = "CONCILIACION", "Conciliacion"


class CuentaBancariaEmpresa(TenantRelationValidationMixin, BaseModel):
    """Cuenta bancaria propia de la empresa para flujos de tesoreria."""

    tenant_fk_fields = ["moneda"]

    alias = models.CharField(max_length=100)
    banco = models.CharField(max_length=120)
    tipo_cuenta = models.CharField(max_length=20, choices=TipoCuentaBancoEmpresa.choices)
    numero_cuenta = models.CharField(max_length=50)
    titular = models.CharField(max_length=150)
    moneda = models.ForeignKey(
        "core.Moneda",
        on_delete=models.PROTECT,
        related_name="cuentas_bancarias_empresa",
    )
    saldo_referencial = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero_cuenta"],
                name="uniq_cuenta_bancaria_empresa_numero",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activa"]),
            models.Index(fields=["empresa", "banco"]),
        ]

    def clean(self):
        super().clean()
        if Decimal(self.saldo_referencial or 0) < 0:
            raise ValidationError({"saldo_referencial": "El saldo referencial no puede ser negativo."})

    def save(self, *args, **kwargs):
        self.alias = normalizar_texto(self.alias)
        self.banco = normalizar_texto(self.banco)
        self.titular = normalizar_texto(self.titular)
        self.numero_cuenta = str(self.numero_cuenta or "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alias} - {self.banco}"


class MovimientoBancario(TenantRelationValidationMixin, BaseModel):
    """Movimiento bancario manual/importado para conciliacion de tesoreria."""

    tenant_fk_fields = ["cuenta_bancaria", "cuenta_por_cobrar", "cuenta_por_pagar"]

    cuenta_bancaria = models.ForeignKey(
        "core.CuentaBancariaEmpresa",
        on_delete=models.CASCADE,
        related_name="movimientos_bancarios",
    )
    fecha = models.DateField()
    referencia = models.CharField(max_length=120, blank=True)
    descripcion = models.CharField(max_length=255, blank=True)
    tipo = models.CharField(max_length=20, choices=TipoMovimientoBancario.choices)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    origen = models.CharField(
        max_length=20,
        choices=OrigenMovimientoBancario.choices,
        default=OrigenMovimientoBancario.MANUAL,
    )
    estado_contable = models.CharField(
        max_length=20,
        choices=EstadoContable.choices,
        default=EstadoContable.NO_APLICA,
    )
    conciliado = models.BooleanField(default=False)
    conciliado_en = models.DateTimeField(null=True, blank=True)
    cuenta_por_cobrar = models.ForeignKey(
        "core.CuentaPorCobrar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_bancarios",
    )
    cuenta_por_pagar = models.ForeignKey(
        "core.CuentaPorPagar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_bancarios",
    )

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "fecha"]),
            models.Index(fields=["empresa", "conciliado"]),
            models.Index(fields=["empresa", "cuenta_bancaria", "fecha"]),
        ]

    def clean(self):
        super().clean()
        if Decimal(self.monto or 0) <= 0:
            raise ValidationError({"monto": "El monto del movimiento debe ser mayor a cero."})
        if self.cuenta_por_cobrar_id and self.cuenta_por_pagar_id:
            raise ValidationError("Un movimiento no puede conciliarse con CxC y CxP al mismo tiempo.")

    def save(self, *args, **kwargs):
        self.referencia = normalizar_texto(self.referencia)
        self.descripcion = normalizar_texto(self.descripcion)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha} {self.tipo} {self.monto}"
