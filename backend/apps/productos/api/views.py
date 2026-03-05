from rest_framework.viewsets import ModelViewSet
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
