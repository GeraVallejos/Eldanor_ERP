from decimal import Decimal

from django.db import models

from apps.core.mixins import AuditDiffMixin, TenantRelationValidationMixin
from apps.documentos.models import DocumentoTributableBase


class EstadoFacturaVenta(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    EMITIDA = "EMITIDA", "Emitida"
    ANULADA = "ANULADA", "Anulada"


class FacturaVenta(AuditDiffMixin, TenantRelationValidationMixin, DocumentoTributableBase):
    """Factura de venta. Documento tributario que genera cuenta por cobrar."""

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="facturas_venta",
    )

    pedido_venta = models.ForeignKey(
        "ventas.PedidoVenta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facturas_venta",
    )

    guia_despacho = models.ForeignKey(
        "ventas.GuiaDespacho",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facturas_venta",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoFacturaVenta.choices,
        default=EstadoFacturaVenta.BORRADOR,
    )

    fecha_emision = models.DateField()

    fecha_vencimiento = models.DateField(
        help_text="Fecha límite de pago.",
    )

    descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Porcentaje de descuento global (0-100).",
    )

    # Folio tributario asignado por integración SII (facturación electrónica).
    folio_tributario = models.CharField(max_length=50, blank=True)

    emitido_por = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facturas_venta_emitidas",
    )

    emitido_en = models.DateTimeField(null=True, blank=True)

    anulado_por = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facturas_venta_anuladas",
    )

    anulado_en = models.DateTimeField(null=True, blank=True)

    tenant_fk_fields = ["cliente", "pedido_venta", "guia_despacho"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="unique_numero_factura_venta_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "cliente"]),
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "fecha_emision"]),
            models.Index(fields=["empresa", "fecha_vencimiento"]),
            models.Index(fields=["empresa", "pedido_venta"]),
        ]
        ordering = ["-fecha_emision"]

    def clean(self):
        super().clean()
        if self.fecha_vencimiento and self.fecha_emision and self.fecha_vencimiento < self.fecha_emision:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                {"fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la emisión."}
            )
        if Decimal(self.descuento or 0) < 0 or Decimal(self.descuento or 0) > 100:
            from django.core.exceptions import ValidationError
            raise ValidationError({"descuento": "El descuento debe estar entre 0 y 100."})

    def __str__(self):
        return f"FV {self.numero}"
