import os
from apps.core.tenant import set_current_empresa, set_current_user

# Para subir el logo del cliente a Cloudflare R2, con un nombre fijo para que se sobreescriba cada vez que se suba uno nuevo
def logo_upload_path(instance, filename):
    # 1. Extraemos la extensión original (.jpg, .png, etc.)
    extension = os.path.splitext(filename)[1].lower()
    
    # 2. Definimos un nombre fijo
    nuevo_nombre = f"logo_principal{extension}"
    
    # 3. Retornamos la ruta: logos/UUID/logo_principal.ext
    # Al ser el mismo nombre, Cloudflare R2 sobrescribirá el anterior 
    # si el storage está configurado para permitirlo.
    return f"logos/{instance.id}/{nuevo_nombre}"



# Función para tests: Setear el tenant actual (empresa y usuario) en el contexto global
def set_test_tenant(empresa, user=None):
    set_current_empresa(empresa)
    if user:
        set_current_user(user)