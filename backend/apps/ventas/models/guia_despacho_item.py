from decimal import Decimal

from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.documentos.models import DocumentoItemBase


class GuiaDespachoItem(TenantRelationValidationMixin, DocumentoItemBase):
    """Item de guía de despacho. Vinculado opcionalmente a item de pedido para trazabilidad."""

    guia_despacho = models.ForeignKey(
        "ventas.GuiaDespacho",
        on_delete=models.CASCADE,
        related_name="items",
    )

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="guia_despacho_items",
    )

    pedido_item = models.ForeignKey(
        "ventas.PedidoVentaItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guia_despacho_items",
        help_text="Item de pedido de origen para trazabilidad de despacho.",
    )

    impuesto_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    tenant_fk_fields = ["guia_despacho", "producto", "impuesto", "pedido_item"]

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "guia_despacho"]),
            models.Index(fields=["empresa", "pedido_item"]),
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
