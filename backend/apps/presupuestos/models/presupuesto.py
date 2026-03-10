from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import AuditDiffMixin, TenantRelationValidationMixin
from apps.documentos.models import DocumentoBase


class EstadoPresupuesto(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ENVIADO = "ENVIADO", "Enviado"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    ANULADO = "ANULADO", "Anulado"


class Presupuesto(AuditDiffMixin, TenantRelationValidationMixin, DocumentoBase):
    tenant_fk_fields = ["cliente"]

    numero = models.PositiveIntegerField()

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="presupuestos",
    )

    fecha = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=EstadoPresupuesto.choices,
        default=EstadoPresupuesto.BORRADOR,
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impuesto_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["-fecha"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="unique_numero_per_empresa",
            )
        ]

    def clean(self):
        super().clean()

        if self.descuento is not None and Decimal(self.descuento) < 0:
            raise ValidationError({"descuento": "El descuento no puede ser negativo."})

        if self.fecha and self.fecha_vencimiento and self.fecha_vencimiento < self.fecha:
            raise ValidationError(
                {
                    "fecha_vencimiento": (
                        "La fecha de vencimiento no puede ser anterior a la fecha de emision."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                original = Presupuesto.all_objects.get(pk=self.pk)
                if (
                    original.estado == EstadoPresupuesto.APROBADO
                    and self.estado == EstadoPresupuesto.APROBADO
                ):
                    raise ValidationError(
                        "No se puede modificar un presupuesto ya aprobado. "
                        "Para realizar cambios, anule este y clone uno nuevo."
                    )
            except Presupuesto.DoesNotExist:
                pass

        if not self.fecha_vencimiento and self.fecha:
            from datetime import timedelta
            from django.utils.dateparse import parse_date

            fecha_dt = parse_date(self.fecha) if isinstance(self.fecha, str) else self.fecha
            if fecha_dt:
                self.fecha_vencimiento = fecha_dt + timedelta(days=15)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero} - {self.cliente}"
