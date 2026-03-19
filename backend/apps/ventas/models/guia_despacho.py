from django.db import models

from apps.core.mixins import AuditDiffMixin, TenantRelationValidationMixin
from apps.documentos.models import DocumentoTributableBase


class EstadoGuiaDespacho(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    ANULADA = "ANULADA", "Anulada"


class GuiaDespacho(AuditDiffMixin, TenantRelationValidationMixin, DocumentoTributableBase):
    """Guía de despacho. Documento de salida de mercadería con movimiento de inventario."""

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="guias_despacho",
    )

    pedido_venta = models.ForeignKey(
        "ventas.PedidoVenta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guias_despacho",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoGuiaDespacho.choices,
        default=EstadoGuiaDespacho.BORRADOR,
    )

    fecha_despacho = models.DateField()

    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="guias_despacho",
        help_text="Bodega de origen. Si no se especifica, se usa la bodega principal.",
    )

    confirmado_por = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guias_despacho_confirmadas",
    )

    confirmado_en = models.DateTimeField(null=True, blank=True)

    anulado_por = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guias_despacho_anuladas",
    )

    anulado_en = models.DateTimeField(null=True, blank=True)

    tenant_fk_fields = ["cliente", "pedido_venta", "bodega"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="unique_numero_guia_despacho_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "cliente"]),
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "pedido_venta"]),
            models.Index(fields=["empresa", "fecha_despacho"]),
        ]
        ordering = ["-fecha_despacho"]

    def __str__(self):
        return f"GD {self.numero}"
