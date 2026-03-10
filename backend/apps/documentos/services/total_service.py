from decimal import Decimal


class DocumentTotalsService:

    @staticmethod
    def calcular_totales(documento, *, persist=True):

        subtotal = Decimal("0")
        impuestos = Decimal("0")

        for item in documento.items.all():

            subtotal += item.subtotal
            impuestos += item.total - item.subtotal

        documento.subtotal = subtotal

        # Presupuesto usa impuesto_total; compras usa impuestos.
        if hasattr(documento, "impuestos"):
            documento.impuestos = impuestos

        if hasattr(documento, "impuesto_total"):
            documento.impuesto_total = impuestos

        documento.total = subtotal + impuestos

        if persist:
            update_fields = ["subtotal", "total"]
            if hasattr(documento, "impuestos"):
                update_fields.append("impuestos")
            if hasattr(documento, "impuesto_total"):
                update_fields.append("impuesto_total")
            documento.save(update_fields=update_fields)

        return documento