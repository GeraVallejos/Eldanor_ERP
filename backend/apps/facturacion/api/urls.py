from rest_framework.routers import DefaultRouter

from apps.facturacion.api.views import ConfiguracionTributariaViewSet, RangoFolioTributarioViewSet


router = DefaultRouter()
router.register(r"configuracion-tributaria", ConfiguracionTributariaViewSet, basename="configuracion-tributaria")
router.register(r"rangos-folios-tributarios", RangoFolioTributarioViewSet, basename="rango-folio-tributario")

urlpatterns = router.urls

