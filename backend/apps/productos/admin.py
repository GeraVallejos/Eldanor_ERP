from django.contrib import admin
from django.utils.html import format_html
from apps.core.admin import BulkImportAdminMixin, TenantAdminMixin
from apps.core.tenant import set_current_empresa, set_current_user
from .models.producto import Producto
from .models.categoria import Categoria
from .models.impuesto import Impuesto
from ..inventario.models.movimiento import MovimientoInventario, TipoMovimiento
from .services.bulk_import_service import bulk_import_productos, build_productos_bulk_template

class MovimientoInventarioInline(TenantAdminMixin, admin.TabularInline):
    model = MovimientoInventario
    extra = 0
    readonly_fields = ('tipo', 'cantidad', 'stock_anterior', 'stock_nuevo', 'referencia', 'creado_en')
    can_delete = False # El historial no se debería poder borrar

    def has_add_permission(self, request, obj=None):
        return False # Los movimientos se crean por Service, no a mano en el inline

@admin.register(Producto)
class ProductoAdmin(BulkImportAdminMixin, TenantAdminMixin, admin.ModelAdmin):
    change_list_template = 'admin/bulk_import_change_list.html'
    bulk_import_title = 'Carga masiva productos'
    list_display = ('nombre', 'sku', 'tipo', 'categoria', 'color_stock', 'activo', 'empresa', 'creado_por')
    list_filter = ('tipo', 'categoria', 'activo')
    search_fields = ('nombre', 'sku')
    inlines = [MovimientoInventarioInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'nombre', 'sku', 'tipo', 'categoria', 'activo')
        }),
        ('Precios e Impuestos', {
            'fields': ('moneda', 'precio_referencia', 'precio_costo', 'impuesto')
        }),
        ('Inventario', {
            'fields': (
                'unidad_medida',
                'permite_decimales',
                'maneja_inventario',
                'stock_actual',
                'stock_minimo',
                'usa_lotes',
                'usa_series',
                'usa_vencimiento',
            )
        }),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if request.user.is_superuser:
            return fieldsets

        filtered = []
        for section_name, options in fieldsets:
            fields = tuple(
                field for field in options.get('fields', ())
                if field not in ('empresa', 'creado_por')
            )
            filtered.append((section_name, {**options, 'fields': fields}))

        return tuple(filtered)

    def color_stock(self, obj):
        """Le da color al stock en la lista para identificar faltantes rápido"""
        if not obj.maneja_inventario:
            return "N/A"
        
        color = "green" if obj.stock_actual > 0 else "red"
        return format_html(
            '<b style="color: {};">{}</b>',
            color,
            obj.stock_actual
        )
    color_stock.short_description = "Stock Actual"

    def handle_bulk_import(self, request, uploaded_file):
        empresa = self._resolve_empresa_for_user(request.user)
        set_current_user(request.user)
        set_current_empresa(empresa)
        return bulk_import_productos(uploaded_file=uploaded_file, user=request.user, empresa=empresa)

    def handle_bulk_template(self, request):
        empresa = self._resolve_empresa_for_user(request.user)
        set_current_user(request.user)
        set_current_empresa(empresa)
        content = build_productos_bulk_template(user=request.user, empresa=empresa)
        return content, 'plantilla_productos.xlsx'

@admin.register(Categoria)
class CategoriaAdmin(TenantAdminMixin,admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'activa')


@admin.register(Impuesto)
class ImpuestoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('nombre', 'porcentaje')
   

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(TenantAdminMixin,admin.ModelAdmin):
    list_display = ('creado_en', 'producto', 'tipo', 'cantidad', 'stock_nuevo', 'referencia')
    list_filter = ('tipo', 'creado_en')
    search_fields = ('producto__nombre', 'referencia')
    readonly_fields = ('empresa', 'creado_por')