from rest_framework.routers import DefaultRouter

from .views import (
    DocumentoCompraProveedorItemViewSet,
    DocumentoCompraProveedorViewSet,
    OrdenCompraItemViewSet,
    OrdenCompraViewSet,
    RecepcionCompraItemViewSet,
    RecepcionCompraViewSet,
)

router = DefaultRouter()
router.register(r"ordenes-compra", OrdenCompraViewSet, basename="orden-compra")
router.register(r"ordenes-compra-items", OrdenCompraItemViewSet, basename="orden-compra-item")
router.register(r"recepciones-compra", RecepcionCompraViewSet, basename="recepcion-compra")
router.register(r"recepciones-compra-items", RecepcionCompraItemViewSet, basename="recepcion-compra-item")
router.register(r"documentos-compra", DocumentoCompraProveedorViewSet, basename="documento-compra")
router.register(r"documentos-compra-items", DocumentoCompraProveedorItemViewSet, basename="documento-compra-item")

urlpatterns = router.urls
