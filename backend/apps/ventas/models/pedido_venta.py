from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import AuditDiffMixin, TenantRelationValidationMixin
from apps.documentos.models import DocumentoTributableBase


class EstadoPedidoVenta(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    EN_PROCESO = "EN_PROCESO", "En proceso"
    DESPACHADO = "DESPACHADO", "Despachado"
    FACTURADO = "FACTURADO", "Facturado"
    ANULADO = "ANULADO", "Anulado"


class PedidoVenta(AuditDiffMixin, TenantRelationValidationMixin, DocumentoTributableBase):
    """Pedido de venta. Documento comercial no tributario, base del flujo ventas."""

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="pedidos_venta",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoPedidoVenta.choices,
        default=EstadoPedidoVenta.BORRADOR,
    )

    fecha_emision = models.DateField()

    fecha_entrega = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de entrega comprometida.",
    )

    descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Porcentaje de descuento global sobre el total (0-100).",
    )

    lista_precio = models.ForeignKey(
        "productos.ListaPrecio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_venta",
    )

    tenant_fk_fields = ["cliente", "lista_precio"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero"],
                name="unique_numero_pedido_venta_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "cliente"]),
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "fecha_emision"]),
        ]
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"PV {self.numero}"

    def clean(self):
        super().clean()
        if Decimal(self.descuento or 0) < 0 or Decimal(self.descuento or 0) > 100:
            raise ValidationError({"descuento": "El descuento debe estar entre 0 y 100."})
        if self.fecha_entrega and self.fecha_emision and self.fecha_entrega < self.fecha_emision:
            raise ValidationError(
                {"fecha_entrega": "La fecha de entrega no puede ser anterior a la emisión."}
            )
