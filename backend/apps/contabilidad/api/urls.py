from rest_framework.routers import DefaultRouter

from apps.contabilidad.api.views import AsientoContableViewSet, MovimientoContableViewSet, PlanCuentaViewSet

router = DefaultRouter()
router.register(r"plan-cuentas", PlanCuentaViewSet, basename="plan-cuenta")
router.register(r"asientos-contables", AsientoContableViewSet, basename="asiento-contable")
router.register(r"movimientos-contables", MovimientoContableViewSet, basename="movimiento-contable")

urlpatterns = router.urls
