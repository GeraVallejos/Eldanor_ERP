from rest_framework.routers import DefaultRouter
from .views import (
	CategoriaViewSet,
	ImpuestoViewSet,
	ListaPrecioItemViewSet,
	ListaPrecioViewSet,
	ProductoViewSet,
)

router = DefaultRouter()
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"categorias", CategoriaViewSet, basename="categoria")
router.register(r"impuestos", ImpuestoViewSet, basename="impuesto")
router.register(r"listas-precio", ListaPrecioViewSet, basename="lista-precio")
router.register(r"listas-precio-items", ListaPrecioItemViewSet, basename="lista-precio-item")

urlpatterns = router.urls