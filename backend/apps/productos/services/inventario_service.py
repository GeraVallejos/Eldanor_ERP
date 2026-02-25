from django.db import transaction
from django.core.exceptions import ValidationError
from apps.productos.models.producto import Producto
from ..models.movimiento import MovimientoInventario, TipoMovimiento

class InventarioService:
    @staticmethod
    @transaction.atomic
    def registrar_movimiento(producto, tipo, cantidad, referencia, empresa, usuario):
        """
        Registra un movimiento en el Kardex y actualiza el stock del producto.
        """
        producto = Producto.objects.select_for_update().get(pk=producto.pk, empresa=empresa)
        
        if not producto.maneja_inventario:
            raise ValidationError(f"El producto {producto.nombre} no maneja inventario.")

        if cantidad <= 0:
            raise ValidationError("La cantidad del movimiento debe ser mayor a cero.")

        # 1. Guardar estado anterior
        stock_anterior = producto.stock_actual

        # 2. Calcular nuevo stock
        if tipo == TipoMovimiento.ENTRADA:
            nuevo_stock = stock_anterior + cantidad
        else:
            nuevo_stock = stock_anterior - cantidad
            # Validar si permitimos stock negativo
            if nuevo_stock < 0:
                raise ValidationError(f"Stock insuficiente para {producto.nombre}.")

        # 3. Crear el registro en el Kardex
        movimiento = MovimientoInventario.objects.create(
            producto=producto,
            tipo=tipo,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            referencia=referencia,
            empresa=empresa,
            creado_por=usuario
        )

        # 4. Actualizar el producto
        producto.stock_actual = nuevo_stock
        producto.save(skip_clean=True) # Saltamos validación pesada si ya validamos aquí

        return movimiento