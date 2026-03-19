from decimal import Decimal

from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.documentos.models import DocumentoItemBase


class NotaCreditoVentaItem(TenantRelationValidationMixin, DocumentoItemBase):
    """Item de nota de crédito de venta con referencia opcional a item de factura original."""

    nota_credito = models.ForeignKey(
        "ventas.NotaCreditoVenta",
        on_delete=models.CASCADE,
        related_name="items",
    )

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="nota_credito_venta_items",
    )

    factura_item = models.ForeignKey(
        "ventas.FacturaVentaItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nota_credito_items",
        help_text="Item de factura original para trazabilidad.",
    )

    impuesto_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    tenant_fk_fields = ["nota_credito", "producto", "impuesto", "factura_item"]

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "nota_credito"]),
        ]

    def save(self, *args, **kwargs):
        if self.producto_id and not self.descripcion:
            self.descripcion = self.producto.nombre
        if self.impuesto_id and not self.impuesto_porcentaje:
            self.impuesto_porcentaje = Decimal(self.impuesto.porcentaje or 0)

        cantidad = Decimal(self.cantidad or 0)
        precio = Decimal(self.precio_unitario or 0)
        tasa = Decimal(self.impuesto_porcentaje or 0)

        subtotal = (cantidad * precio).quantize(Decimal("0.01"))
        impuesto_monto = (subtotal * tasa / Decimal("100")).quantize(Decimal("0.01"))

        self.subtotal = subtotal
        self.total = (subtotal + impuesto_monto).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.descripcion or str(self.producto_id)
