from django.urls import path
from apps.core.api.views import (
    AplicarPlantillaPermisosView,
    CambiarEmpresaActivaView,
    CustomTokenObtainPairView,
    EmpresasUsuarioView,
    PlantillaPermisosDetalleView,
    PlantillasPermisosView,
    CatalogoPermisosView,
    MiembrosEmpresaPermisosView,
    GestionPermisosUsuarioEmpresaView,
)


urlpatterns = [
    path("cambiar-empresa-activa/",CambiarEmpresaActivaView.as_view(),name="cambiar-empresa-activa"),
    path("empresas-usuario/",EmpresasUsuarioView.as_view(),name="empresas-usuario"),
    path("permisos/catalogo/", CatalogoPermisosView.as_view(), name="permisos-catalogo"),
    path("permisos/miembros-empresa/", MiembrosEmpresaPermisosView.as_view(), name="permisos-miembros-empresa"),
    path("permisos/asignar/", GestionPermisosUsuarioEmpresaView.as_view(), name="permisos-asignar"),
    path("permisos/plantillas/", PlantillasPermisosView.as_view(), name="permisos-plantillas"),
    path("permisos/plantillas/aplicar/", AplicarPlantillaPermisosView.as_view(), name="permisos-plantillas-aplicar"),
    path("permisos/plantillas/<str:codigo>/", PlantillaPermisosDetalleView.as_view(), name="permisos-plantillas-detalle"),
]