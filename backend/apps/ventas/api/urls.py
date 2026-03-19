from rest_framework.routers import DefaultRouter

from apps.ventas.api.views import (
    FacturaVentaItemViewSet,
    FacturaVentaViewSet,
    GuiaDespachoItemViewSet,
    GuiaDespachoViewSet,
    NotaCreditoVentaItemViewSet,
    NotaCreditoVentaViewSet,
    PedidoVentaItemViewSet,
    PedidoVentaViewSet,
)

router = DefaultRouter()
router.register(r"pedidos-venta", PedidoVentaViewSet, basename="pedido-venta")
router.register(r"pedidos-venta-items", PedidoVentaItemViewSet, basename="pedido-venta-item")
router.register(r"guias-despacho", GuiaDespachoViewSet, basename="guia-despacho")
router.register(r"guias-despacho-items", GuiaDespachoItemViewSet, basename="guia-despacho-item")
router.register(r"facturas-venta", FacturaVentaViewSet, basename="factura-venta")
router.register(r"facturas-venta-items", FacturaVentaItemViewSet, basename="factura-venta-item")
router.register(r"notas-credito-venta", NotaCreditoVentaViewSet, basename="nota-credito-venta")
router.register(
    r"notas-credito-venta-items",
    NotaCreditoVentaItemViewSet,
    basename="nota-credito-venta-item",
)

urlpatterns = router.urls
