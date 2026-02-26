import re
from django.core.exceptions import ValidationError

def formatear_rut(rut_sucio: str) -> str:
    if not rut_sucio:
        return rut_sucio

    limpio = "".join(
        x for x in rut_sucio if x.isdigit() or x.upper() == "K"
    ).upper()

    if len(limpio) < 2:
        return limpio

    cuerpo = limpio[:-1]
    dv = limpio[-1]

    if not cuerpo.isdigit():
        return limpio

    cuerpo_con_puntos = f"{int(cuerpo):,}".replace(",", ".")

    return f"{cuerpo_con_puntos}-{dv}"

def validar_rut(rut: str):
    """
    Valida formato de RUT chileno.
    """
    rut_regex = r'^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$'
    if not re.match(rut_regex, rut):
        raise ValidationError(f'RUT inválido: {rut}')

def validar_rut_unico_por_modelo(modelo, empresa, rut, instance_id=None):
    """
    Valida que el RUT sea único para un MODELO específico y una empresa.
    """
    if rut:
        # Filtramos dinámicamente según el modelo que le pasemos
        qs = modelo.objects.filter(empresa=empresa, rut=rut)
        if instance_id:
            qs = qs.exclude(pk=instance_id)
        if qs.exists():
            nombre_modelo = modelo._meta.verbose_name.capitalize()
            raise ValidationError(f"Este RUT ya está registrado como {nombre_modelo} en esta empresa.")
        
def normalizar_texto(valor, es_email=False):
    if not valor or not isinstance(valor, str):
        return valor
    
    # Limpiar espacios extra: "  juan   perez  " -> "juan perez"
    limpio = " ".join(valor.split())
    
    if es_email:
        return limpio.lower()
    
    return limpio.upper()