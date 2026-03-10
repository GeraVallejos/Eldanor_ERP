from rest_framework.routers import DefaultRouter

from .views import BodegaViewSet, InventorySnapshotViewSet, MovimientoInventarioViewSet, StockProductoViewSet

router = DefaultRouter()
router.register(r"bodegas", BodegaViewSet, basename="bodega")
router.register(r"stocks", StockProductoViewSet, basename="stock-producto")
router.register(r"movimientos-inventario", MovimientoInventarioViewSet, basename="movimiento-inventario")
router.register(r"inventario-snapshots", InventorySnapshotViewSet, basename="inventario-snapshot")

urlpatterns = router.urls
