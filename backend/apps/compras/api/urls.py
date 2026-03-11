from rest_framework.routers import DefaultRouter

from .views import (
    DocumentoCompraProveedorItemViewSet,
    DocumentoCompraProveedorViewSet,
    OrdenCompraItemViewSet,
    OrdenCompraViewSet,
)

router = DefaultRouter()
router.register(r"ordenes-compra", OrdenCompraViewSet, basename="orden-compra")
router.register(r"ordenes-compra-items", OrdenCompraItemViewSet, basename="orden-compra-item")
router.register(r"documentos-compra", DocumentoCompraProveedorViewSet, basename="documento-compra")
router.register(r"documentos-compra-items", DocumentoCompraProveedorItemViewSet, basename="documento-compra-item")

urlpatterns = router.urls
