from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import Empresa

User = get_user_model()

class TenantAdminMixin:
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(empresa=request.user.empresa)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.empresa = request.user.empresa
        super().save_model(request, obj, form, change)

@admin.register(User)
class CustomUserAdmin(TenantAdminMixin, UserAdmin): # <-- Agregamos el Mixin
    list_display = ("username", "email", "empresa", "is_staff", "is_active")
    
    fieldsets = UserAdmin.fieldsets + (
        ("Información de ERP", {"fields": ("empresa", "rol", "telefono")}),
    )

    def get_readonly_fields(self, request, obj=None):
        # Si no es superusuario, no puede editar a qué empresa pertenece nadie
        if not request.user.is_superuser:
            return ("empresa",)
        return super().get_readonly_fields(request, obj)

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    # Aquí NO usamos el mixin porque si un usuario normal viera esto, 
    # solo vería su propia empresa. Generalmente, este modelo 
    # es solo para que el Superuser gestione suscripciones.
    list_display = ("nombre", "rut", "plan", "activa")
    search_fields = ("nombre", "rut")

    def has_module_permission(self, request):
        # Solo el Superuser ve el módulo "Empresas" en el panel lateral
        return request.user.is_superuser

