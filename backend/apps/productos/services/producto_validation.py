from apps.productos.validators import (
    validate_non_negative,
    validate_stock,
    validate_same_empresa,
)


def clean_producto(instance):
    """
    Valida coherencia estructural del producto.
    Recibe la instancia completa.
    """

    validate_same_empresa(instance.categoria, instance, "categoria")
    validate_same_empresa(instance.impuesto, instance, "impuesto")

    # Validaciones numéricas
    validate_non_negative(instance.precio_costo, "precio costo")
    validate_non_negative(instance.precio_referencia, "precio referencia")

    # Validación inventario
    validate_stock(
        instance.tipo,
        instance.maneja_inventario,
        instance.stock_actual
    )

