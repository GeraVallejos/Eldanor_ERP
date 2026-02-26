from django.contrib import admin
from  apps.core.admin import TenantAdminMixin
from .models.contacto import Contacto
from .models.cliente import Cliente
from .models.proveedor import Proveedor
from .models.direccion import Direccion
from .models.cuentaBancaria import CuentaBancaria

# --- Inlines ---

class DireccionInline(admin.StackedInline):
    model = Direccion
    extra = 0
    fieldsets = (
        (None, {
            'fields': (('tipo', 'pais'), 'direccion', ('comuna', 'ciudad', 'region'))
        }),
    )

class CuentaBancariaInline(admin.StackedInline):
    model = CuentaBancaria
    extra = 0
    fieldsets = (
        (None, {
            'fields': (('banco', 'tipo_cuenta'), 'numero_cuenta', ('titular', 'rut_titular'), 'activa')
        }),
    )

# --- ModelAdmins ---

@admin.register(Contacto)
class ContactoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'tipo', 'email', 'telefono', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre', 'rut', 'razon_social')
    readonly_fields = ('empresa', 'creado_por')
    inlines = [DireccionInline, CuentaBancariaInline]

    def get_queryset(self, request):
        # 1. Llamamos al queryset original (que ahora gracias al Manager corregido trae todo)
        qs = super().get_queryset(request)
        
        # 2. Si es superusuario, permitimos ver todo el universo de datos
        if request.user.is_superuser:
            return qs
            
        # 3. Filtramos estrictamente por la empresa del usuario identificado
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        
        # 4. Si por alguna razón el usuario no tiene empresa asignada,
        # devolvemos vacío por seguridad para evitar fugas de datos.
        return qs.none()
    
   

@admin.register(Cliente)
class ClienteAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('get_nombre', 'get_rut', 'limite_credito', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')
    readonly_fields = ('get_empresa', 'get_creado_por')

    def get_empresa(self, obj):
        return obj.contacto.empresa if obj.contacto else "-"
    get_empresa.short_description = 'Empresa'

    def get_creado_por(self, obj):
        return obj.contacto.creado_por if obj.contacto else "-"
    get_creado_por.short_description = 'Creado por'

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'

@admin.register(Proveedor)
class ProveedorAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('get_nombre', 'get_rut', 'giro', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')
    readonly_fields = ('get_empresa', 'get_creado_por')

    def get_empresa(self, obj):
        return obj.contacto.empresa if obj.contacto else "-"
    get_empresa.short_description = 'Empresa'

    def get_creado_por(self, obj):
        return obj.contacto.creado_por if obj.contacto else "-"
    get_creado_por.short_description = 'Creado por'

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'
