from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum


class CalculoVentasService:
    """Servicio de cálculo de totales para documentos y líneas del módulo ventas."""

    @classmethod
    def redondear(cls, valor):
        """Redondea a 2 decimales con ROUND_HALF_UP."""
        return Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calcular_totales_item(cls, *, cantidad, precio_unitario, porcentaje_descuento=0, tasa_impuesto=0):
        """Calcula subtotal, impuesto y total para una línea de documento de venta."""
        cantidad = Decimal(str(cantidad or 0))
        precio = Decimal(str(precio_unitario or 0))
        descuento = Decimal(str(porcentaje_descuento or 0))
        tasa = Decimal(str(tasa_impuesto or 0))

        bruto = cls.redondear(cantidad * precio)
        descuento_monto = cls.redondear(bruto * descuento / Decimal("100"))
        subtotal = cls.redondear(bruto - descuento_monto)
        impuesto_monto = cls.redondear(subtotal * tasa / Decimal("100"))
        total = cls.redondear(subtotal + impuesto_monto)

        return {
            "subtotal": subtotal,
            "impuesto_monto": impuesto_monto,
            "total": total,
        }

    @classmethod
    def recalcular_documento(cls, *, documento, items_qs):
        """
        Recalcula subtotal, impuestos y total de un documento sumando sus items.
        Persiste los cambios en la base de datos.
        """
        agg = items_qs.aggregate(
            subtotal_sum=Sum("subtotal", default=Decimal("0")),
            total_sum=Sum("total", default=Decimal("0")),
        )
        subtotal = cls.redondear(agg["subtotal_sum"])
        total = cls.redondear(agg["total_sum"])
        impuestos = cls.redondear(total - subtotal)

        documento.subtotal = subtotal
        documento.impuestos = impuestos
        documento.total = total
        documento.save(update_fields=["subtotal", "impuestos", "total"])
        return documento
