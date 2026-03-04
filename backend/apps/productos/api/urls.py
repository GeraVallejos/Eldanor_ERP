from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, CategoriaViewSet, ImpuestoViewSet

router = DefaultRouter()
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"categorias", CategoriaViewSet, basename="categoria")
router.register(r"impuestos", ImpuestoViewSet, basename="impuesto")

urlpatterns = router.urls