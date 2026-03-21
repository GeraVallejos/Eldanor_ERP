from rest_framework.routers import DefaultRouter

from apps.tesoreria.api.views import (
    CuentaBancariaEmpresaViewSet,
    CuentaPorCobrarViewSet,
    CuentaPorPagarViewSet,
    MonedaViewSet,
    MovimientoBancarioViewSet,
    TipoCambioViewSet,
)

router = DefaultRouter()
router.register(r"monedas", MonedaViewSet, basename="moneda")
router.register(r"tipos-cambio", TipoCambioViewSet, basename="tipo-cambio")
router.register(r"cuentas-bancarias", CuentaBancariaEmpresaViewSet, basename="cuenta-bancaria")
router.register(r"movimientos-bancarios", MovimientoBancarioViewSet, basename="movimiento-bancario")
router.register(r"cuentas-por-cobrar", CuentaPorCobrarViewSet, basename="cuenta-por-cobrar")
router.register(r"cuentas-por-pagar", CuentaPorPagarViewSet, basename="cuenta-por-pagar")

urlpatterns = router.urls
