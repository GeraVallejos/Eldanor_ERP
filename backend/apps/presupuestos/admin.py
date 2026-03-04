from django.contrib import admin
from django.utils.safestring import mark_safe
from apps.core.admin import TenantAdminMixin
from .models import Presupuesto, PresupuestoItem, PresupuestoHistorial


class PresupuestoItemInline(admin.TabularInline):
    model = PresupuestoItem
    extra = 0
    readonly_fields = ('subtotal', 'total', 'impuesto_porcentaje')

@admin.register(Presupuesto)
class PresupuestoAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('numero', 'cliente', 'fecha', 'estado', 'total')
    list_filter = ('estado', 'fecha')
    search_fields = ('numero', 'cliente__nombre')
    inlines = [PresupuestoItemInline]

@admin.register(PresupuestoHistorial)
class PresupuestoHistorialAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ('presupuesto', 'usuario', 'estado_anterior', 'estado_nuevo', 'creado_en')
    readonly_fields = ('presupuesto', 'usuario', 'estado_anterior', 'estado_nuevo', 'cambios_formateados', 'creado_en')
    exclude = ('cambios',) # Ocultamos el JSON crudo

    def cambios_formateados(self, obj):
        if not obj.cambios:
            return "Sin cambios detallados"
        
        html = "<ul>"
        for campo, valores in obj.cambios.items():
            antes = valores.get('antes', 'N/A')
            despues = valores.get('despues', 'N/A')
            html += f"<li><strong>{campo}</strong>: <span style='color:red;'>{antes}</span> → <span style='color:green;'>{despues}</span></li>"
        html += "</ul>"
        return mark_safe(html)
    
    cambios_formateados.short_description = "Detalle de cambios"

