from rest_framework.routers import DefaultRouter
from .views import ContactoViewSet, ClienteViewSet, ProveedorViewSet, CuentaBancariaViewSet, DireccionViewSet

router = DefaultRouter()
router.register(r"contactos/cuentas-bancarias", CuentaBancariaViewSet, basename="contacto-cuenta-bancaria")
router.register(r"contactos", ContactoViewSet, basename="contacto")
router.register(r"clientes", ClienteViewSet, basename="cliente")
router.register(r"proveedores", ProveedorViewSet, basename="proveedor")
router.register(r"direcciones", DireccionViewSet, basename="direccion")
urlpatterns = router.urls
