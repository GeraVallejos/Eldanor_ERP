from django.urls import path
from apps.core.api.views import CambiarEmpresaActivaView, CustomTokenObtainPairView, EmpresasUsuarioView


urlpatterns = [
    path("cambiar-empresa-activa/",CambiarEmpresaActivaView.as_view(),name="cambiar-empresa-activa"),
    path("empresas-usuario/",EmpresasUsuarioView.as_view(),name="empresas-usuario"),
]