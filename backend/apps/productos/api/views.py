from rest_framework.viewsets import ModelViewSet
from apps.productos.models import Producto
from apps.productos.api.serializer import ProductoSerializer
from apps.core.mixins import TenantViewSetMixin


class ProductoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Producto
    serializer_class = ProductoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        print(f"DEBUG API: Usuario {self.request.user} - Empresa {self.request.user.empresa}")
        print(f"DEBUG API: Registros encontrados: {qs.count()}")
        return qs
