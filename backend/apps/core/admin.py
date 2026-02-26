from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import Empresa

User = get_user_model()

class TenantAdminMixin:
    def get_queryset(self, request):
        # Usamos el queryset estándar del Admin
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Filtrar Contacto, Producto, Categoria, etc.
        if hasattr(self.model, 'empresa'):
            return qs.filter(empresa=request.user.empresa)
        
        # Filtrar Cliente, Proveedor
        if hasattr(self.model, 'contacto'):
            return qs.filter(contacto__empresa=request.user.empresa)
        
        return qs

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if hasattr(obj, 'empresa'):
                obj.empresa = request.user.empresa
            
            if not change and hasattr(obj, 'creado_por'):
                obj.creado_por = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra lo que aparece en los select/combos del formulario"""
        if not request.user.is_superuser:
            related_model = db_field.remote_field.model
            
            # Si el modelo relacionado tiene el campo 'empresa'
            if hasattr(related_model, 'empresa'):
                # Priorizamos usar all_objects para que el Manager restrictivo 
                # de la API no interfiera con la carga del combo en el Admin
                if hasattr(related_model, 'all_objects'):
                    base_qs = related_model.all_objects.all()
                else:
                    base_qs = related_model.objects.all()
                
                # Aplicamos el filtro de empresa manualmente
                kwargs["queryset"] = base_qs.filter(empresa=request.user.empresa)
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(User)
class CustomUserAdmin(TenantAdminMixin, UserAdmin): # <-- Agregamos el Mixin
    list_display = ("username", "email", "empresa", "is_staff", "is_active")
    
    fieldsets = UserAdmin.fieldsets + (
        ("Información de ERP", {"fields": ("empresa", "rol", "telefono")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "username",
                "first_name",
                "last_name",
                "password1",
                "password2",
                "empresa",
                "rol",
                "is_staff",
                "is_active",
            ),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        # Si no es superusuario, no puede editar a qué empresa pertenece nadie
        if not request.user.is_superuser:
            return ("empresa",)
        return super().get_readonly_fields(request, obj)

@admin.register(Empresa)
class EmpresaAdmin(TenantAdminMixin, admin.ModelAdmin):
    # Aquí NO usamos el mixin porque si un usuario normal viera esto, 
    # solo vería su propia empresa. Generalmente, este modelo 
    # es solo para que el Superuser gestione suscripciones.
    list_display = ("nombre", "rut", "plan", "activa")
    search_fields = ("nombre", "rut")

    def has_module_permission(self, request):
        # Solo el Superuser ve el módulo "Empresas" en el panel lateral
        return request.user.is_superuser

