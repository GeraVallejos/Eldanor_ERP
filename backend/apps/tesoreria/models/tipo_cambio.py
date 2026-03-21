from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models.base import BaseModel


class TipoCambio(BaseModel):
    """Historial de tipo de cambio por fecha para conversion de documentos."""

    moneda_origen = models.ForeignKey(
        "tesoreria.Moneda",
        on_delete=models.PROTECT,
        related_name="tipos_cambio_origen",
    )
    moneda_destino = models.ForeignKey(
        "tesoreria.Moneda",
        on_delete=models.PROTECT,
        related_name="tipos_cambio_destino",
    )
    fecha = models.DateField()
    tasa = models.DecimalField(max_digits=18, decimal_places=6)
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "tesoreria_tipocambio"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "moneda_origen", "moneda_destino", "fecha"],
                name="uniq_tipo_cambio_por_fecha",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "fecha"], name="tes_tipocambio_emp_fec_idx"),
            models.Index(
                fields=["empresa", "moneda_origen", "moneda_destino", "fecha"],
                name="tes_tipocambio_emp_mon_fec_idx",
            ),
        ]
        ordering = ["-fecha"]

    def clean(self):
        super().clean()

        if self.moneda_origen_id == self.moneda_destino_id:
            raise ValidationError("La moneda origen y destino deben ser distintas.")

        if self.moneda_origen and self.moneda_origen.empresa_id != self.empresa_id:
            raise ValidationError({"moneda_origen": "La moneda origen no pertenece a la empresa."})

        if self.moneda_destino and self.moneda_destino.empresa_id != self.empresa_id:
            raise ValidationError({"moneda_destino": "La moneda destino no pertenece a la empresa."})

        if Decimal(self.tasa or 0) <= 0:
            raise ValidationError({"tasa": "La tasa debe ser mayor a cero."})

    def __str__(self):
        return f"{self.moneda_origen.codigo}/{self.moneda_destino.codigo} {self.fecha}"
