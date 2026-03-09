from django.db import transaction
from apps.core.exceptions import BusinessRuleError
from apps.productos.models.producto import Producto
from apps.productos.models.movimiento import MovimientoInventario, TipoMovimiento


class InventarioService:

    @staticmethod
    @transaction.atomic
    def registrar_movimiento(
        *,
        producto_id,
        tipo,
        cantidad,
        referencia,
        empresa,
        usuario
    ):
        """
        Registra un movimiento en el Kardex y actualiza el stock del producto.
        """

        if cantidad <= 0:
            raise BusinessRuleError("La cantidad debe ser mayor a cero.")

        if tipo not in TipoMovimiento.values:
            raise BusinessRuleError("Tipo de movimiento inválido.")

        # Bloqueo seguro multiempresa
        # Evitamos depender del contexto tenant implícito: el servicio ya recibe empresa.
        producto = (
            Producto.all_objects
            .select_for_update()
            .get(pk=producto_id, empresa=empresa)
        )

        if not producto.maneja_inventario:
            raise BusinessRuleError(
                f"El producto {producto.nombre} no maneja inventario."
            )

        stock_anterior = producto.stock_actual

        # Calcular nuevo stock
        if tipo == TipoMovimiento.ENTRADA:
            nuevo_stock = stock_anterior + cantidad

        elif tipo == TipoMovimiento.SALIDA:
            nuevo_stock = stock_anterior - cantidad

            if nuevo_stock < 0:
                raise BusinessRuleError(
                    f"Stock insuficiente para {producto.nombre}. "
                    f"Disponible: {stock_anterior}"
                )

        # 📝 Crear movimiento
        movimiento = MovimientoInventario.all_objects.create(
            producto=producto,
            tipo=tipo,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            referencia=referencia,
            empresa=empresa,
            creado_por=usuario
        )

        # 💾 Actualizar producto
        producto.stock_actual = nuevo_stock
        producto.save(skip_clean=True, update_fields=["stock_actual"])

        return movimiento