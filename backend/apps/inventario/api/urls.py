from rest_framework.routers import DefaultRouter

from .views import (
    AjusteInventarioMasivoViewSet,
    BodegaViewSet,
    InventorySnapshotViewSet,
    MovimientoInventarioViewSet,
    StockLoteViewSet,
    StockProductoViewSet,
    TrasladoInventarioMasivoViewSet,
)

router = DefaultRouter()
router.register(r"bodegas", BodegaViewSet, basename="bodega")
router.register(r"lotes", StockLoteViewSet, basename="stock-lote")
router.register(r"stocks", StockProductoViewSet, basename="stock-producto")
router.register(r"movimientos-inventario", MovimientoInventarioViewSet, basename="movimiento-inventario")
router.register(r"inventario-snapshots", InventorySnapshotViewSet, basename="inventario-snapshot")
router.register(r"ajustes-masivos", AjusteInventarioMasivoViewSet, basename="ajuste-inventario-masivo")
router.register(r"traslados-masivos", TrasladoInventarioMasivoViewSet, basename="traslado-inventario-masivo")

urlpatterns = router.urls
