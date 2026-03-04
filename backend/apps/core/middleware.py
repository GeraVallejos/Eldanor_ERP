from .tenant import set_current_empresa, set_current_user

class EmpresaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            set_current_user(user)
            set_current_empresa(getattr(user, "empresa_activa", None))

        try:
            response = self.get_response(request)
        finally:
            set_current_user(None)
            set_current_empresa(None)

        return response