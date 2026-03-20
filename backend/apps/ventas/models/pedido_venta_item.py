from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.mixins import TenantRelationValidationMixin
from apps.documentos.models import DocumentoItemBase


class PedidoVentaItem(TenantRelationValidationMixin, DocumentoItemBase):
    """Item de pedido de venta con precio, descuento e impuesto desnormalizados."""

    pedido_venta = models.ForeignKey(
        "ventas.PedidoVenta",
        on_delete=models.CASCADE,
        related_name="items",
    )

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pedido_venta_items",
    )

    presupuesto_item_origen = models.ForeignKey(
        "presupuestos.PresupuestoItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedido_venta_items",
        help_text="Item de presupuesto origen para trazabilidad comercial y control de consumo.",
    )

    descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Porcentaje de descuento por línea (0-100).",
    )

    impuesto_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Tasa de impuesto desnormalizada al momento del pedido.",
    )

    tenant_fk_fields = ["pedido_venta", "producto", "impuesto", "presupuesto_item_origen"]

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "pedido_venta"]),
            models.Index(fields=["empresa", "presupuesto_item_origen"]),
        ]

    def save(self, *args, **kwargs):
        # Auto-completar descripción y porcentaje de impuesto desde el producto.
        if self.producto_id and not self.descripcion:
            self.descripcion = self.producto.nombre
        if self.impuesto_id and not self.impuesto_porcentaje:
            self.impuesto_porcentaje = Decimal(self.impuesto.porcentaje or 0)

        descuento = Decimal(self.descuento or 0)
        if descuento < 0 or descuento > 100:
            raise ValidationError({"descuento": "El descuento debe estar entre 0 y 100."})

        cantidad = Decimal(self.cantidad or 0)
        precio = Decimal(self.precio_unitario or 0)
        tasa = Decimal(self.impuesto_porcentaje or 0)

        bruto = (cantidad * precio).quantize(Decimal("0.01"))
        descuento_monto = (bruto * descuento / Decimal("100")).quantize(Decimal("0.01"))
        subtotal = (bruto - descuento_monto).quantize(Decimal("0.01"))
        impuesto_monto = (subtotal * tasa / Decimal("100")).quantize(Decimal("0.01"))

        self.subtotal = subtotal
        self.total = (subtotal + impuesto_monto).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.descripcion or str(self.producto_id)
