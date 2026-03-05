from .tenant import set_current_empresa, set_current_user
from .models import UserEmpresa

class EmpresaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            set_current_user(user)
            empresa_activa = getattr(user, "empresa_activa", None)

            # Solo seteamos empresa si la relación está activa para este usuario.
            if user.is_superuser:
                set_current_empresa(empresa_activa)
            elif empresa_activa and UserEmpresa.objects.filter(
                user=user,
                empresa=empresa_activa,
                activo=True,
            ).exists():
                set_current_empresa(empresa_activa)
            else:
                set_current_empresa(None)
        else:
            set_current_user(None)
            set_current_empresa(None)

        try:
            response = self.get_response(request)
        finally:
            set_current_user(None)
            set_current_empresa(None)

        return response