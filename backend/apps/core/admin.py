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
            return qs.filter(empresa=request.user.empresa_activa)
        
        # Filtrar Cliente, Proveedor
        if hasattr(self.model, 'contacto'):
            return qs.filter(contacto__empresa=request.user.empresa_activa)
        
        return qs
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            # En lugar de agregar 'empresa', agregamos el nombre del método que crearemos abajo
            if hasattr(self.model, 'empresa'):
                if 'empresa' in readonly: readonly.remove('empresa') # Quitamos el original
                readonly.append('show_empresa_text')
            
            if hasattr(self.model, 'creado_por'):
                if 'creado_por' in readonly: readonly.remove('creado_por')
                readonly.append('show_creado_por_text')
        return readonly

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            # Creamos una lista limpia
            clean_fields = []
            for f in fields:
                # Si es el campo real, lo ignoramos (porque ya usaremos el 'show_..._text')
                if f in ['empresa', 'creado_por']:
                    continue
                # Si es una de nuestras funciones 'get_...' manuales antiguas, las quitamos
                if str(f).startswith('get_empresa') or str(f).startswith('get_creado'):
                    continue
                clean_fields.append(f)
            return clean_fields
        return fields

    # Métodos para mostrar solo TEXTO sin LINK
    def show_empresa_text(self, obj):
        return obj.empresa.nombre if obj and obj.empresa else "-"
    show_empresa_text.short_description = "Empresa"

    def show_creado_por_text(self, obj):
        return obj.creado_por.username if obj and obj.creado_por else "-"
    show_creado_por_text.short_description = "Creado por"

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if hasattr(obj, 'empresa'):
                obj.empresa = request.user.empresa_activa
            
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
                kwargs["queryset"] = base_qs.filter(empresa=request.user.empresa_activa)
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



@admin.register(User)
class CustomUserAdmin(TenantAdminMixin, UserAdmin):
    
    list_display = ("username", "email", "empresa_activa", "is_staff", "is_active")
    
    fieldsets = UserAdmin.fieldsets + (
        ("Información de ERP", {"fields": ("empresa_activa", "telefono")}),
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
                "empresa_activa",
                "is_staff",
                "is_active",
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        # 1. Obtenemos los fieldsets base (que ya traen is_superuser, etc.)
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if not request.user.is_superuser:
            # 2. Convertimos a una estructura editable (listas de listas)
            new_fieldsets = []
            for name, content in fieldsets:
                fields = list(content.get('fields', []))
                
                # REGLA A: Cambiar 'empresa' por nuestro texto sin link
                if 'empresa_activa' in fields:
                    fields[fields.index('empresa_activa')] = 'show_empresa_text'
                
                # REGLA B: Eliminar permisos críticos para no-superusers
                # Quitamos is_superuser, user_permissions y groups
                fields = [f for f in fields if f not in ('is_superuser', 'user_permissions', 'groups')]
                
                new_fieldsets.append((name, {'fields': tuple(fields)}))
            return tuple(new_fieldsets)
            
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        # Usamos la lógica del Mixin pero aseguramos 'show_empresa_text'
        readonly = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            # Forzamos que estos campos sean siempre texto plano
            if 'show_empresa_text' not in readonly:
                readonly.append('show_empresa_text')
            # Si el usuario intenta editar su propio staff status, lo bloqueamos
            if 'is_staff' not in readonly:
                readonly.append('is_staff')
        return readonly

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

