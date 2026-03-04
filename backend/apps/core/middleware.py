from .tenant import set_current_empresa, set_current_user
from rest_framework_simplejwt.authentication import JWTAuthentication

class EmpresaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = None
        
        # 1. Intentar obtener usuario desde la sesión (Django Admin / Web)
        if request.user.is_authenticated:
            user = request.user
        else:
            # 2. Intentar obtener usuario desde el Token (API Rest)
            try:
                auth = JWTAuthentication().authenticate(request)
                if auth:
                    user, _ = auth
            except Exception:
                user = None

        # 3. Establecer el contexto global
        if user and user.is_authenticated:
    
            empresa_activa = user.empresa_activa

            if empresa_activa and user.empresas_rel.filter(
                empresa=empresa_activa,
                activo=True
            ).exists():
                
                set_current_user(user)
                set_current_empresa(empresa_activa)
            else:
                set_current_user(user)
                set_current_empresa(None)

        # 4. Procesar la petición
        try:
            response = self.get_response(request)
        finally:
            # 5. LIMPIEZA ABSOLUTA: Se ejecuta siempre, incluso si falla la DB o hay un error 500.
            # Esto evita que los datos de una empresa "sangren" a la siguiente petición.
            set_current_user(None)
            set_current_empresa(None)
            
        return response