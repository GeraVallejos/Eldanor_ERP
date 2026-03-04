from rest_framework.routers import DefaultRouter
from .views import PresupuestoViewSet

router = DefaultRouter()
router.register(r"presupuestos", PresupuestoViewSet, basename="presupuesto")  

urlpatterns = router.urls