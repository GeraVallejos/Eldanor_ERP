from django.db import models

from apps.core.mixins import AuditDiffMixin, TenantRelationValidationMixin
from apps.documentos.models import DocumentoTributableBase


class EstadoNotaCreditoVenta(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    EMITIDA = "EMITIDA", "Emitida"
    ANULADA = "ANULADA", "Anulada"


class TipoNotaCreditoVenta(models.TextChoices):
    ANULACION = "ANULACION", "Anulación de factura"
    DESCUENTO = "DESCUENTO", "Descuento post-factura"
    DEVOLUCION = "DEVOLUCION", "Devolución de mercadería"
    CORRECCION = "CORRECCION", "Corrección de precio"


class NotaCreditoVenta(AuditDiffMixin, TenantRelationValidationMixin, DocumentoTributableBase):
    """Nota de crédito de venta. Revierte o ajusta parcialmente una factura emitida."""

    factura_origen = models.ForeignKey(
        "ventas.FacturaVenta",
        on_delete=models.PROTECT,
        related_name="notas_credito",
        help_text="Factura de venta que origina la nota de crédito.",
    )

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="notas_credito_venta",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoNotaCreditoVenta.choices,
        default=EstadoNotaCreditoVenta.BORRADOR,
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoNotaCreditoVenta.choices,
        default=TipoNotaCreditoVenta.ANULACION,
    )

    fecha_emision = models.DateField()

    motivo = models.TextField(
        help_text="Motivo de la emisión de la nota de crédito.",
    )

    # Folio tributario asignado por integración SII.
    folio_tributario = models.CharField(max_length=50, blank=True)

    emitido_por = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas_credito_emitidas",
    )

    emitido_en = models.DateTimeField(null=True, blank=True)

    anulado_por = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notas_credito_anuladas",
    )

    anulado_en = models.DateTimeField(null=True, blank=True)

    tenant_fk_fields = ["factura_origen", "cliente"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="unique_numero_nota_credito_venta_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "cliente"]),
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "factura_origen"]),
            models.Index(fields=["empresa", "fecha_emision"]),
        ]
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"NC {self.numero}"
