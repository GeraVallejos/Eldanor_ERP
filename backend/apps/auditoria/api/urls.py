from rest_framework.routers import DefaultRouter

from .views import AuditEventViewSet

router = DefaultRouter()
router.register(r"auditoria/eventos", AuditEventViewSet, basename="auditoria-evento")

urlpatterns = router.urls
