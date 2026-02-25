from django.contrib import admin
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
class ContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'tipo', 'email', 'telefono', 'activo')
    list_filter = ('tipo', 'activo', 'empresa')
    search_fields = ('nombre', 'rut', 'razon_social')
    inlines = [DireccionInline, CuentaBancariaInline]
    
    # Esto asegura que el contacto se asocie a la empresa del usuario actual
    def save_model(self, request, obj, form, change):
        if not obj.empresa_id:
            obj.empresa = request.user.empresa # Asumiendo que tu User tiene relación a Empresa
        super().save_model(request, obj, form, change)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('get_nombre', 'get_rut', 'limite_credito', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('get_nombre', 'get_rut', 'giro', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'
