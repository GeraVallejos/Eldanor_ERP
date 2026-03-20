from rest_framework.routers import DefaultRouter

from apps.contabilidad.api.views import (
    AsientoContableViewSet,
    ConfiguracionCuentaContableViewSet,
    MovimientoContableViewSet,
    PlanCuentaViewSet,
)

router = DefaultRouter()
router.register(r"plan-cuentas", PlanCuentaViewSet, basename="plan-cuenta")
router.register(r"configuracion-cuentas-contables", ConfiguracionCuentaContableViewSet, basename="configuracion-cuenta-contable")
router.register(r"asientos-contables", AsientoContableViewSet, basename="asiento-contable")
router.register(r"movimientos-contables", MovimientoContableViewSet, basename="movimiento-contable")

urlpatterns = router.urls
