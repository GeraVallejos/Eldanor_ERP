import re
from django.core.exceptions import ValidationError
from .models.cliente import Cliente

def validar_rut(rut: str):
    """
    Valida formato de RUT chileno.
    """
    rut_regex = r'^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$'
    if not re.match(rut_regex, rut):
        raise ValidationError(f'RUT inválido: {rut}')

def validar_rut_unico(empresa, rut, instance_id=None):
    """
    Valida que el RUT sea único por empresa.
    """
    if rut:
        qs = Cliente.objects.filter(empresa=empresa, rut=rut)
        if instance_id:
            qs = qs.exclude(pk=instance_id)
        if qs.exists():
            raise ValidationError(f"El RUT {rut} ya existe en esta empresa.")