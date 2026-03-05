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


@admin.register(Cliente)
class ClienteAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('get_nombre', 'get_rut', 'limite_credito', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')
    

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'

@admin.register(Proveedor)
class ProveedorAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('get_nombre', 'get_rut', 'giro', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')
    

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'
