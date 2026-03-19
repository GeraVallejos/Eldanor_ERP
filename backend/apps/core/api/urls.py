from rest_framework.routers import DefaultRouter

from django.urls import path
from apps.core.api.views import (
    AplicarPlantillaPermisosView,
    CambiarEmpresaActivaView,
    CuentaPorCobrarViewSet,
    CuentaPorPagarViewSet,
    LogoutView,
    MeView,
    CustomTokenRefreshView,
    CustomTokenObtainPairView,
    EmpresasUsuarioView,
    PlantillaPermisosDetalleView,
    PlantillasPermisosView,
    CatalogoPermisosView,
    MiembrosEmpresaPermisosView,
    GestionPermisosUsuarioEmpresaView,
    EmpresaLogoView,
    MonedaViewSet,
    TipoCambioViewSet,
)


router = DefaultRouter()
router.register(r"monedas", MonedaViewSet, basename="moneda")
router.register(r"tipos-cambio", TipoCambioViewSet, basename="tipo-cambio")
router.register(r"cuentas-por-cobrar", CuentaPorCobrarViewSet, basename="cuenta-por-cobrar")
router.register(r"cuentas-por-pagar", CuentaPorPagarViewSet, basename="cuenta-por-pagar")


urlpatterns = [
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", MeView.as_view(), name="auth_me"),
    path("auth/empresa-logo/", EmpresaLogoView.as_view(), name="auth_empresa_logo"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    path("cambiar-empresa-activa/",CambiarEmpresaActivaView.as_view(),name="cambiar-empresa-activa"),
    path("empresas-usuario/",EmpresasUsuarioView.as_view(),name="empresas-usuario"),
    path("permisos/catalogo/", CatalogoPermisosView.as_view(), name="permisos-catalogo"),
    path("permisos/miembros-empresa/", MiembrosEmpresaPermisosView.as_view(), name="permisos-miembros-empresa"),
    path("permisos/asignar/", GestionPermisosUsuarioEmpresaView.as_view(), name="permisos-asignar"),
    path("permisos/plantillas/", PlantillasPermisosView.as_view(), name="permisos-plantillas"),
    path("permisos/plantillas/aplicar/", AplicarPlantillaPermisosView.as_view(), name="permisos-plantillas-aplicar"),
    path("permisos/plantillas/<str:codigo>/", PlantillaPermisosDetalleView.as_view(), name="permisos-plantillas-detalle"),
] + router.urls
