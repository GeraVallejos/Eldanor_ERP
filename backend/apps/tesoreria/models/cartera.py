from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models.base import BaseModel


class EstadoCuenta(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    PARCIAL = "PARCIAL", "Parcial"
    PAGADA = "PAGADA", "Pagada"
    VENCIDA = "VENCIDA", "Vencida"
    ANULADA = "ANULADA", "Anulada"


class CuentaPorCobrar(BaseModel):
    """Cuenta por cobrar orientada a futuras ventas/facturacion."""

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="cuentas_por_cobrar",
    )
    moneda = models.ForeignKey(
        "tesoreria.Moneda",
        on_delete=models.PROTECT,
        related_name="cuentas_por_cobrar",
    )
    referencia = models.CharField(max_length=100)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    monto_total = models.DecimalField(max_digits=14, decimal_places=2)
    saldo = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=20, choices=EstadoCuenta.choices, default=EstadoCuenta.PENDIENTE)

    class Meta:
        db_table = "tesoreria_cuentaporcobrar"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "referencia"],
                name="uniq_cxc_referencia_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "cliente", "estado"], name="tes_cxc_emp_cli_est_idx"),
            models.Index(fields=["empresa", "fecha_vencimiento"], name="tes_cxc_emp_ven_idx"),
        ]

    def clean(self):
        super().clean()
        if Decimal(self.monto_total or 0) < 0:
            raise ValidationError({"monto_total": "El monto total no puede ser negativo."})
        if Decimal(self.saldo or 0) < 0:
            raise ValidationError({"saldo": "El saldo no puede ser negativo."})
        if self.saldo > self.monto_total:
            raise ValidationError({"saldo": "El saldo no puede superar el monto total."})


class CuentaPorPagar(BaseModel):
    """Cuenta por pagar orientada a compras y tesoreria."""

    proveedor = models.ForeignKey(
        "contactos.Proveedor",
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar",
    )
    moneda = models.ForeignKey(
        "tesoreria.Moneda",
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar",
    )
    documento_compra = models.OneToOneField(
        "compras.DocumentoCompraProveedor",
        on_delete=models.PROTECT,
        related_name="cuenta_por_pagar",
        null=True,
        blank=True,
    )
    referencia = models.CharField(max_length=100)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    monto_total = models.DecimalField(max_digits=14, decimal_places=2)
    saldo = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=20, choices=EstadoCuenta.choices, default=EstadoCuenta.PENDIENTE)

    class Meta:
        db_table = "tesoreria_cuentaporpagar"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "referencia"],
                name="uniq_cxp_referencia_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "proveedor", "estado"], name="tes_cxp_emp_prov_est_idx"),
            models.Index(fields=["empresa", "fecha_vencimiento"], name="tes_cxp_emp_ven_idx"),
        ]

    def clean(self):
        super().clean()
        if Decimal(self.monto_total or 0) < 0:
            raise ValidationError({"monto_total": "El monto total no puede ser negativo."})
        if Decimal(self.saldo or 0) < 0:
            raise ValidationError({"saldo": "El saldo no puede ser negativo."})
        if self.saldo > self.monto_total:
            raise ValidationError({"saldo": "El saldo no puede superar el monto total."})
