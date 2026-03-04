from rest_framework.routers import DefaultRouter
from apps.core.api.views import CambiarEmpresaActivaView, CustomTokenObtainPairView, EmpresasUsuarioView


router = DefaultRouter()
router.register(r"cambiar-empresa-activa", CambiarEmpresaActivaView, basename="cambiar-empresa-activa")
router.register(r"empresas-usuario", EmpresasUsuarioView, basename="empresas-usuario")
urlpatterns = router.urls
