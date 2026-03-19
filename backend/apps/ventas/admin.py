from django.contrib import admin

from apps.ventas.models import (
	FacturaVenta,
	FacturaVentaItem,
	GuiaDespacho,
	GuiaDespachoItem,
	NotaCreditoVenta,
	NotaCreditoVentaItem,
	PedidoVenta,
	PedidoVentaItem,
	VentaHistorial,
)


@admin.register(PedidoVenta)
class PedidoVentaAdmin(admin.ModelAdmin):
	list_display = ("numero", "empresa", "cliente", "estado", "fecha_emision", "total")
	list_filter = ("empresa", "estado", "fecha_emision")
	search_fields = ("numero", "cliente__contacto__nombre")


@admin.register(PedidoVentaItem)
class PedidoVentaItemAdmin(admin.ModelAdmin):
	list_display = ("pedido_venta", "producto", "cantidad", "precio_unitario", "total")
	list_filter = ("empresa",)


@admin.register(GuiaDespacho)
class GuiaDespachoAdmin(admin.ModelAdmin):
	list_display = ("numero", "empresa", "cliente", "estado", "fecha_despacho", "total")
	list_filter = ("empresa", "estado", "fecha_despacho")
	search_fields = ("numero", "cliente__contacto__nombre")


@admin.register(GuiaDespachoItem)
class GuiaDespachoItemAdmin(admin.ModelAdmin):
	list_display = ("guia_despacho", "producto", "cantidad", "precio_unitario", "total")
	list_filter = ("empresa",)


@admin.register(FacturaVenta)
class FacturaVentaAdmin(admin.ModelAdmin):
	list_display = ("numero", "empresa", "cliente", "estado", "fecha_emision", "total")
	list_filter = ("empresa", "estado", "fecha_emision")
	search_fields = ("numero", "folio_tributario", "cliente__contacto__nombre")


@admin.register(FacturaVentaItem)
class FacturaVentaItemAdmin(admin.ModelAdmin):
	list_display = ("factura_venta", "producto", "cantidad", "precio_unitario", "total")
	list_filter = ("empresa",)


@admin.register(NotaCreditoVenta)
class NotaCreditoVentaAdmin(admin.ModelAdmin):
	list_display = ("numero", "empresa", "cliente", "estado", "fecha_emision", "total")
	list_filter = ("empresa", "estado", "tipo", "fecha_emision")
	search_fields = ("numero", "folio_tributario", "cliente__contacto__nombre")


@admin.register(NotaCreditoVentaItem)
class NotaCreditoVentaItemAdmin(admin.ModelAdmin):
	list_display = ("nota_credito", "producto", "cantidad", "precio_unitario", "total")
	list_filter = ("empresa",)


@admin.register(VentaHistorial)
class VentaHistorialAdmin(admin.ModelAdmin):
	list_display = ("tipo_documento", "documento_id", "estado_anterior", "estado_nuevo", "creado_en")
	list_filter = ("empresa", "tipo_documento", "estado_nuevo", "creado_en")
