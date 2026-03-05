from decimal import Decimal, ROUND_HALF_UP

class CalculoService:

    @staticmethod
    def redondear(valor):
        """Asegura que cualquier Decimal tenga exactamente 2 decimales."""
        if not isinstance(valor, Decimal):
            valor = Decimal(str(valor))
        return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calcular_totales_item(cls, cantidad, precio_unitario, porcentaje_descuento, tasa_impuesto):
        # 1. Calculamos subtotal bruto
        subtotal_bruto = Decimal(cantidad) * Decimal(precio_unitario)
        
        # 2. Descuento (Calculamos y redondeamos de inmediato)
        monto_descuento = cls.redondear(subtotal_bruto * (Decimal(porcentaje_descuento) / 100))
        
        # 3. Subtotal Neto
        subtotal_neto = cls.redondear(subtotal_bruto - monto_descuento)
        
        # 4. Impuesto sobre el neto
        monto_impuesto = cls.redondear(subtotal_neto * (Decimal(tasa_impuesto) / 100))
        
        # 5. Total final
        total = cls.redondear(subtotal_neto + monto_impuesto)
        
        return {
            "subtotal": subtotal_neto,
            "impuesto": monto_impuesto,
            "descuento": monto_descuento,
            "total": total
        }

    @classmethod
    def recalcular_presupuesto(cls, presupuesto):
        items = presupuesto.items.all()
        nuevo_subtotal = Decimal("0.00")
        nuevo_impuesto = Decimal("0.00")
        descuento_global = Decimal(presupuesto.descuento or 0)

        for item in items:
            nuevo_subtotal += item.subtotal
            # El impuesto aquí lo derivamos o lo puedes guardar en el item
            nuevo_impuesto += (item.total - item.subtotal)

        presupuesto.subtotal = cls.redondear(nuevo_subtotal)
        presupuesto.impuesto_total = cls.redondear(nuevo_impuesto)
        total_bruto = cls.redondear(nuevo_subtotal + nuevo_impuesto)
        # Descuento de cabecera aplicado al total del documento.
        presupuesto.total = cls.redondear(max(Decimal("0.00"), total_bruto - descuento_global))
        
        presupuesto.save(update_fields=['subtotal', 'impuesto_total', 'total'])
