from .tenant import set_current_empresa


class EmpresaMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        empresa = None  # 👈 siempre inicializar

        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            empresa = getattr(user, "empresa", None)

            if empresa and not empresa.activa:
                from django.http import JsonResponse
                return JsonResponse({"detail": "Empresa inactiva"}, status=403)

        # siempre seteamos algo (aunque sea None)
        set_current_empresa(empresa)

        response = self.get_response(request)
        return response