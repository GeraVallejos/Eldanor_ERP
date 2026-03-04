from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from apps.core.api.views import CustomTokenObtainPairView

urlpatterns = [

     # JWT
    path("api/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Admin
    path('admin/', admin.site.urls),
    # APIs
    path("api/", include("apps.productos.api.urls")),
    path("api/", include("apps.contactos.api.urls")),
    path("api/", include("apps.presupuestos.api.urls")),
]
