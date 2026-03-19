import django_filters

from apps.ventas.models import (
    EstadoFacturaVenta,
    EstadoGuiaDespacho,
    EstadoNotaCreditoVenta,
    EstadoPedidoVenta,
    FacturaVenta,
    GuiaDespacho,
    NotaCreditoVenta,
    PedidoVenta,
)


class PedidoVentaFilter(django_filters.FilterSet):
    estado = django_filters.MultipleChoiceFilter(choices=EstadoPedidoVenta.choices)
    cliente = django_filters.UUIDFilter(field_name="cliente_id")
    fecha_desde = django_filters.DateFilter(field_name="fecha_emision", lookup_expr="gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_emision", lookup_expr="lte")
    numero = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = PedidoVenta
        fields = ["estado", "cliente", "fecha_desde", "fecha_hasta", "numero"]


class GuiaDespachoFilter(django_filters.FilterSet):
    estado = django_filters.MultipleChoiceFilter(choices=EstadoGuiaDespacho.choices)
    cliente = django_filters.UUIDFilter(field_name="cliente_id")
    pedido_venta = django_filters.UUIDFilter(field_name="pedido_venta_id")
    fecha_desde = django_filters.DateFilter(field_name="fecha_despacho", lookup_expr="gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_despacho", lookup_expr="lte")
    numero = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = GuiaDespacho
        fields = ["estado", "cliente", "pedido_venta", "fecha_desde", "fecha_hasta", "numero"]


class FacturaVentaFilter(django_filters.FilterSet):
    estado = django_filters.MultipleChoiceFilter(choices=EstadoFacturaVenta.choices)
    cliente = django_filters.UUIDFilter(field_name="cliente_id")
    pedido_venta = django_filters.UUIDFilter(field_name="pedido_venta_id")
    fecha_desde = django_filters.DateFilter(field_name="fecha_emision", lookup_expr="gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_emision", lookup_expr="lte")
    numero = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = FacturaVenta
        fields = ["estado", "cliente", "pedido_venta", "fecha_desde", "fecha_hasta", "numero"]


class NotaCreditoVentaFilter(django_filters.FilterSet):
    estado = django_filters.MultipleChoiceFilter(choices=EstadoNotaCreditoVenta.choices)
    cliente = django_filters.UUIDFilter(field_name="cliente_id")
    factura_origen = django_filters.UUIDFilter(field_name="factura_origen_id")
    fecha_desde = django_filters.DateFilter(field_name="fecha_emision", lookup_expr="gte")
    fecha_hasta = django_filters.DateFilter(field_name="fecha_emision", lookup_expr="lte")
    numero = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = NotaCreditoVenta
        fields = ["estado", "cliente", "factura_origen", "fecha_desde", "fecha_hasta", "numero"]
