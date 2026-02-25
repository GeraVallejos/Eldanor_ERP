from django.core.exceptions import ValidationError
from decimal import Decimal


def validate_non_negative(value, field_name="valor"):
    """
    Valida que un valor numérico no sea negativo.
    """
    if value is None:
        return

    if value < Decimal("0"):
        raise ValidationError(f"El {field_name} no puede ser negativo.")


def validate_stock(tipo, maneja_inventario, stock_actual):
    """
    Reglas de coherencia entre tipo de producto y stock.
    """
    if tipo == "servicio" and stock_actual != 0:
        raise ValidationError("Un servicio no puede tener stock.")

    if maneja_inventario and stock_actual < 0:
        raise ValidationError("El stock no puede ser negativo.")


def normalize_sku(sku):
    """
    Normaliza SKU eliminando espacios y convirtiendo a mayúsculas.
    """
    if not sku:
        return sku

    return sku.strip().upper()


def validate_impuesto_mayor_a_cien(impuesto):
    """
    Valida que el porcentaje de impuesto no sea mayor a 100.
    """
    if impuesto is not None and impuesto > Decimal("100"):
        raise ValidationError("El porcentaje de impuesto no puede ser mayor a 100.")
    
    
def validate_same_empresa(objeto_relacionado, instancia_padre, nombre_campo):
    """
    Valida que un objeto relacionado (ej: Categoria) pertenezca 
    a la misma empresa que la instancia que lo contiene (ej: Producto).
    """
    if objeto_relacionado and objeto_relacionado.empresa_id != instancia_padre.empresa_id:
        raise ValidationError({
            nombre_campo: f"El registro seleccionado de {nombre_campo} no pertenece a su empresa."
        })