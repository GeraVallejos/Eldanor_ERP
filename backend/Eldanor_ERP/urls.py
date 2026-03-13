from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    # APIs
    path("api/", include("apps.core.api.urls")),
    path("api/", include("apps.productos.api.urls")),
    path("api/", include("apps.contactos.api.urls")),
    path("api/", include("apps.presupuestos.api.urls")),
    path("api/", include("apps.compras.api.urls")),
    path("api/", include("apps.inventario.api.urls")),
    path("api/", include("apps.auditoria.api.urls")),
]
