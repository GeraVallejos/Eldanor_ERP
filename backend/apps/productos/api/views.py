from rest_framework.viewsets import ModelViewSet
from apps.productos.models import Producto, Categoria, Impuesto
from apps.productos.api.serializer import ImpuestoSerializer, ProductoSerializer, CategoriaSerializer
from apps.core.mixins import TenantViewSetMixin



class ProductoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Producto
    serializer_class = ProductoSerializer


class CategoriaViewSet(TenantViewSetMixin, ModelViewSet):
    model = Categoria
    serializer_class = CategoriaSerializer


class ImpuestoViewSet(TenantViewSetMixin, ModelViewSet):
    model = Impuesto
    serializer_class = ImpuestoSerializer
