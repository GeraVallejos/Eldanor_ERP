from django.contrib import admin
from django.utils.html import format_html
from .models.producto import Producto
from .models.categoria import Categoria
from .models.impuesto import Impuesto
from .models.movimiento import MovimientoInventario, TipoMovimiento

class MovimientoInventarioInline(admin.TabularInline):
    model = MovimientoInventario
    extra = 0
    readonly_fields = ('tipo', 'cantidad', 'stock_anterior', 'stock_nuevo', 'referencia', 'creado_en')
    can_delete = False # El historial no se debería poder borrar

    def has_add_permission(self, request, obj=None):
        return False # Los movimientos se crean por Service, no a mano en el inline

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sku', 'tipo', 'categoria', 'color_stock', 'activo')
    list_filter = ('tipo', 'categoria', 'activo')
    search_fields = ('nombre', 'sku')
    inlines = [MovimientoInventarioInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'sku', 'tipo', 'categoria', 'activo')
        }),
        ('Precios e Impuestos', {
            'fields': ('precio_referencia', 'precio_costo', 'impuesto')
        }),
        ('Inventario', {
            'fields': ('maneja_inventario', 'stock_actual')
        }),
    )

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

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa')

@admin.register(Impuesto)
class ImpuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'porcentaje')

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('creado_en', 'producto', 'tipo', 'cantidad', 'stock_nuevo', 'referencia')
    list_filter = ('tipo', 'creado_en')
    search_fields = ('producto__nombre', 'referencia')