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
            else:
                relacion_activa = None

                if empresa_activa:
                    relacion_activa = UserEmpresa.objects.filter(
                        user=user,
                        empresa=empresa_activa,
                        activo=True,
                    ).select_related('empresa').first()

                if not relacion_activa:
                    relacion_activa = UserEmpresa.objects.filter(
                        user=user,
                        activo=True,
                    ).select_related('empresa').first()

                    if relacion_activa and user.empresa_activa_id != relacion_activa.empresa_id:
                        user.empresa_activa = relacion_activa.empresa
                        user.save(update_fields=['empresa_activa'])

                set_current_empresa(relacion_activa.empresa if relacion_activa else None)
        else:
            set_current_user(None)
            set_current_empresa(None)

        try:
            response = self.get_response(request)
        finally:
            set_current_user(None)
            set_current_empresa(None)

        return response