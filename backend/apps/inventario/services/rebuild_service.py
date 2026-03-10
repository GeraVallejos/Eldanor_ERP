from apps.inventario.models.movimiento import MovimientoInventario


class InventarioRebuildService:

    @staticmethod
    def rebuild_stock(producto):

        movimientos = (
            MovimientoInventario.objects
            .filter(producto=producto)
            .order_by("creado_en")
        )

        stock = 0

        for m in movimientos:
            if m.tipo == "ENTRADA":
                stock += m.cantidad
            else:
                stock -= m.cantidad

        producto.stock_actual = stock
        producto.save(update_fields=["stock_actual"])