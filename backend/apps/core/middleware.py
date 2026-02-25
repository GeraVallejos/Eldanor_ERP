from .tenant import set_current_empresa, set_current_user

class EmpresaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa = None
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            empresa = getattr(user, "empresa", None)
            if empresa and not empresa.activa:
                from django.http import JsonResponse
                return JsonResponse({"detail": "Empresa inactiva"}, status=403)
            
            set_current_user(user) # Setea el usuario

        set_current_empresa(empresa) # Setea la empresa en el contexto

        response = self.get_response(request)

        # Limpiar contexto al terminar la petición
        set_current_empresa(None)
        set_current_user(None)

        return response