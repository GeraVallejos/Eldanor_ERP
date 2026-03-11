from django.db.models.deletion import ProtectedError
from rest_framework.viewsets import ModelViewSet

from apps.core.exceptions import ConflictError
from apps.core.roles import RolUsuario
from apps.productos.models import Producto, Categoria, Impuesto
from apps.productos.api.serializer import ImpuestoSerializer, ProductoSerializer, CategoriaSerializer
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from rest_framework.permissions import IsAuthenticated



class ProductoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Producto
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self._is_truthy(self.request.query_params.get("include_inactive"))

        if not include_inactive:
            return queryset.filter(activo=True)

        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset

        empresa = self.get_empresa()
        if not empresa:
            return queryset.filter(activo=True)

        rol = user.get_rol_en_empresa(empresa)
        if rol in {RolUsuario.OWNER, RolUsuario.ADMIN}:
            return queryset

        return queryset.filter(activo=True)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        try:
            instance.delete()
        except ProtectedError:
            if not instance.activo:
                raise ConflictError(
                    "El producto ya esta anulado y mantiene referencias historicas."
                )
            # Conserva integridad historica cuando el producto ya fue usado.
            instance.activo = False
            instance.save(skip_clean=True, update_fields=["activo"])


class CategoriaViewSet(TenantViewSetMixin, ModelViewSet):
    model = Categoria
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class ImpuestoViewSet(TenantViewSetMixin, ModelViewSet):
    model = Impuesto
    serializer_class = ImpuestoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }
