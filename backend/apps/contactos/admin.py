from django.contrib import admin
from apps.core.admin import BulkImportAdminMixin, TenantAdminMixin
from apps.core.tenant import set_current_empresa, set_current_user
from .models.contacto import Contacto
from .models.cliente import Cliente
from .models.proveedor import Proveedor
from .models.direccion import Direccion
from .models.cuentaBancaria import CuentaBancaria
from .services.bulk_import_service import (
    import_clientes,
    import_proveedores,
    build_clientes_bulk_template,
    build_proveedores_bulk_template,
)

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
class ClienteAdmin(BulkImportAdminMixin, TenantAdminMixin, admin.ModelAdmin):
    change_list_template = 'admin/bulk_import_change_list.html'
    bulk_import_title = 'Carga masiva clientes'
    list_display = ('get_nombre', 'get_rut', 'limite_credito', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')
    

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'

    def handle_bulk_import(self, request, uploaded_file):
        empresa = self._resolve_empresa_for_user(request.user)
        set_current_user(request.user)
        set_current_empresa(empresa)
        return import_clientes(uploaded_file=uploaded_file, user=request.user, empresa=empresa)

    def handle_bulk_template(self, request):
        empresa = self._resolve_empresa_for_user(request.user)
        set_current_user(request.user)
        set_current_empresa(empresa)
        content = build_clientes_bulk_template(user=request.user, empresa=empresa)
        return content, 'plantilla_clientes.xlsx'

@admin.register(Proveedor)
class ProveedorAdmin(BulkImportAdminMixin, TenantAdminMixin, admin.ModelAdmin):
    change_list_template = 'admin/bulk_import_change_list.html'
    bulk_import_title = 'Carga masiva proveedores'
    list_display = ('get_nombre', 'get_rut', 'giro', 'dias_credito')
    search_fields = ('contacto__nombre', 'contacto__rut')
    

    def get_nombre(self, obj): return obj.contacto.nombre
    def get_rut(self, obj): return obj.contacto.rut
    get_nombre.short_description = 'Nombre'
    get_rut.short_description = 'RUT'

    def handle_bulk_import(self, request, uploaded_file):
        empresa = self._resolve_empresa_for_user(request.user)
        set_current_user(request.user)
        set_current_empresa(empresa)
        return import_proveedores(uploaded_file=uploaded_file, user=request.user, empresa=empresa)

    def handle_bulk_template(self, request):
        empresa = self._resolve_empresa_for_user(request.user)
        set_current_user(request.user)
        set_current_empresa(empresa)
        content = build_proveedores_bulk_template(user=request.user, empresa=empresa)
        return content, 'plantilla_proveedores.xlsx'
