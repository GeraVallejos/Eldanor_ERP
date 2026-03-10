from decimal import Decimal
from django.db import transaction
from apps.core.exceptions import BusinessRuleError
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models.bodega import Bodega
from apps.inventario.models.inventario_snapshot import InventorySnapshot
from apps.productos.models.producto import Producto
from apps.inventario.models.movimiento import MovimientoInventario, TipoMovimiento
from apps.inventario.models.stock_producto import StockProducto


class InventarioService:

    @staticmethod
    def _money(value):
        return Decimal(value).quantize(Decimal("0.01"))

    @staticmethod
    def _cost(value):
        return Decimal(value).quantize(Decimal("0.0001"))

    @staticmethod
    def _resolver_bodega_id(*, empresa, bodega_id):
        if bodega_id:
            existe = Bodega.all_objects.filter(id=bodega_id, empresa=empresa, activa=True).exists()
            if not existe:
                raise BusinessRuleError("La bodega seleccionada no existe o no esta activa.")
            return bodega_id

        bodega_default, _ = Bodega.all_objects.get_or_create(
            empresa=empresa,
            nombre="Principal",
            defaults={"activa": True},
        )
        return bodega_default.id

    @staticmethod
    @transaction.atomic
    def registrar_movimiento(
        *,
        producto_id,
        bodega_id=None,
        tipo,
        cantidad,
        referencia,
        empresa,
        usuario,
        costo_unitario=None,
        documento_tipo=None,
        documento_id=None,
    ):

        if cantidad <= 0:
            raise BusinessRuleError("La cantidad debe ser mayor a cero.")

        cantidad = Decimal(cantidad)

        if tipo not in {TipoMovimiento.ENTRADA, TipoMovimiento.SALIDA}:
            raise BusinessRuleError("Tipo de movimiento invalido.")

        if tipo == TipoMovimiento.ENTRADA and costo_unitario is not None and Decimal(costo_unitario) < 0:
            raise BusinessRuleError("El costo unitario no puede ser negativo.")

        bodega_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_id)

        producto = (
            Producto.all_objects
            .select_for_update()
            .get(pk=producto_id, empresa=empresa)
        )

        if not producto.maneja_inventario:
            raise BusinessRuleError(
                f"El producto {producto.nombre} no maneja inventario."
            )

        stock_obj, _ = (
            StockProducto.all_objects
            .select_for_update()
            .get_or_create(
                empresa=empresa,
                producto=producto,
                bodega_id=bodega_id,
                defaults={
                    "stock": producto.stock_actual,
                    "valor_stock": InventarioService._money(Decimal("0")),
                }
            )
        )

        stock_anterior = stock_obj.stock

        if tipo == TipoMovimiento.ENTRADA:
            nuevo_stock = stock_anterior + cantidad

        else:
            nuevo_stock = stock_anterior - cantidad

            if nuevo_stock < 0:
                raise BusinessRuleError(
                    f"Stock insuficiente para {producto.nombre}"
                )

        # costeo promedio
        if tipo == TipoMovimiento.ENTRADA and costo_unitario is not None:
            costo_unitario = Decimal(costo_unitario)

            valor_existente = producto.stock_actual * producto.costo_promedio
            valor_compra = cantidad * costo_unitario

            nuevo_costo = (
                (valor_existente + valor_compra)
                / (producto.stock_actual + cantidad)
                if (producto.stock_actual + cantidad) > 0
                else costo_unitario
            )

            producto.costo_promedio = InventarioService._cost(nuevo_costo)

        costo_movimiento = (
            costo_unitario
            if (tipo == TipoMovimiento.ENTRADA and costo_unitario is not None)
            else producto.costo_promedio
        )
        costo_movimiento = InventarioService._cost(costo_movimiento)

        valor_total = InventarioService._money(Decimal(cantidad) * Decimal(costo_movimiento))

        if documento_tipo and documento_tipo not in {valor for valor, _ in TipoDocumentoReferencia.choices}:
            raise BusinessRuleError("Tipo de documento invalido para inventario.")

        movimiento = MovimientoInventario.all_objects.create(
            producto=producto,
            bodega_id=bodega_id,
            tipo=tipo,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            costo_unitario=costo_movimiento,
            valor_total=valor_total,
            documento_tipo=documento_tipo,
            documento_id=documento_id,
            referencia=referencia,
            empresa=empresa,
            creado_por=usuario
        )

        stock_obj.stock = nuevo_stock
        stock_obj.valor_stock = InventarioService._money(
            Decimal(nuevo_stock) * Decimal(producto.costo_promedio)
        )
        stock_obj.save(update_fields=["stock", "valor_stock"])

        InventorySnapshot.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            producto=producto,
            bodega_id=bodega_id,
            movimiento=movimiento,
            stock=stock_obj.stock,
            costo_promedio=InventarioService._cost(producto.costo_promedio),
            valor_stock=stock_obj.valor_stock,
        )

        if tipo == TipoMovimiento.ENTRADA:
            producto.stock_actual += cantidad
        else:
            producto.stock_actual -= cantidad

        producto.save(
            skip_clean=True,
            update_fields=["stock_actual", "costo_promedio"]
        )

        return movimiento

    @staticmethod
    def obtener_kardex(
        *,
        empresa,
        producto_id,
        bodega_id=None,
        desde=None,
        hasta=None,
        tipo=None,
        documento_tipo=None,
        referencia=None,
    ):
        queryset = MovimientoInventario.all_objects.filter(empresa=empresa, producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        if desde is not None:
            queryset = queryset.filter(creado_en__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(creado_en__lte=hasta)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if documento_tipo:
            queryset = queryset.filter(documento_tipo=documento_tipo)
        if referencia:
            queryset = queryset.filter(referencia__icontains=referencia)
        return queryset.order_by("creado_en", "id")

    @staticmethod
    def obtener_snapshot(*, empresa, producto_id, bodega_id, hasta=None):
        queryset = InventorySnapshot.all_objects.filter(
            empresa=empresa,
            producto_id=producto_id,
            bodega_id=bodega_id,
        )
        if hasta is not None:
            queryset = queryset.filter(creado_en__lte=hasta)
        return queryset.order_by("-creado_en", "-id").first()