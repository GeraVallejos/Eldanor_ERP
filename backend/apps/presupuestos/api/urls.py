from rest_framework.routers import DefaultRouter
from .views import PresupuestoViewSet, PresupuestoItemViewSet

router = DefaultRouter()
router.register(r"presupuestos", PresupuestoViewSet, basename="presupuesto") 
router.register(r"presupuesto-items", PresupuestoItemViewSet, basename="presupuesto-item")

urlpatterns = router.urls