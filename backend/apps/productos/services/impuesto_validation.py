from apps.productos.validators import (
    validate_non_negative,
    validate_impuesto_mayor_a_cien
)

def clean_impuesto(instance):
    """Valida coherencia estructural del impuesto.
    Recibe la instancia completa.
    """

    # Validacion impuesto
    validate_impuesto_mayor_a_cien(instance.porcentaje)
    validate_non_negative(instance.porcentaje, "porcentaje de impuesto")