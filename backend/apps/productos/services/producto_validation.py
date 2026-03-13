from apps.productos.validators import (
    validate_integer_quantity,
    validate_non_negative,
    validate_traceability_config,
    validate_stock,
    validate_same_empresa,
)


def clean_producto(instance):
    """
    Valida coherencia estructural del producto.
    Recibe la instancia completa.
    """

    if instance.empresa_id:
        validate_same_empresa(instance.categoria, instance, "categoria")
        validate_same_empresa(instance.impuesto, instance, "impuesto")
        validate_same_empresa(instance.moneda, instance, "moneda")
    # Validaciones numéricas
    validate_non_negative(instance.precio_costo, "precio costo")
    validate_non_negative(instance.precio_referencia, "precio referencia")
    validate_non_negative(instance.stock_minimo, "stock minimo")

    # Validación inventario
    validate_stock(
        instance.tipo,
        instance.maneja_inventario,
        instance.stock_actual
    )

    if instance.maneja_inventario and not instance.permite_decimales:
        validate_integer_quantity(instance.stock_actual, "stock_actual")
        validate_integer_quantity(instance.stock_minimo, "stock_minimo")

    validate_traceability_config(
        usa_series=instance.usa_series,
        maneja_inventario=instance.maneja_inventario,
        usa_vencimiento=instance.usa_vencimiento,
        usa_lotes=instance.usa_lotes,
    )

