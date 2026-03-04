from rest_framework.permissions import BasePermission
from apps.core.models import UserEmpresa


class TieneRelacionActiva(BasePermission):
    """
    Verifica que el usuario tenga relación activa
    con la empresa seleccionada.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        empresa = getattr(user, "empresa_activa", None)

        if not empresa:
            return False

        return UserEmpresa.objects.filter(
            user=user,
            empresa=empresa,
            activo=True
        ).exists()