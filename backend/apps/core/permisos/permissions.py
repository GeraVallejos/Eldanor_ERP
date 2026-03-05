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

        if user.is_superuser:
            return True

        empresa = getattr(user, "empresa_activa", None)

        if not empresa:
            return False

        return UserEmpresa.objects.filter(
            user=user,
            empresa=empresa,
            activo=True
        ).exists()


class TienePermisoModuloAccion(BasePermission):
    """
    Aplica control de permisos por módulo/acción en ViewSets.
    Requiere que el View defina:
    - permission_modulo
    - permission_action_map (dict: action DRF -> acción de negocio)
    """

    message = "No tiene permisos para ejecutar esta acción."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        modulo = getattr(view, "permission_modulo", None)
        action_map = getattr(view, "permission_action_map", {})
        drf_action = getattr(view, "action", None)
        accion = action_map.get(drf_action)

        # Si la vista no declara mapping para la acción, no bloqueamos aquí.
        if not modulo or not accion:
            return True

        empresa = getattr(user, "empresa_activa", None)
        if not empresa:
            return False

        return user.tiene_permiso(modulo, accion, empresa)
