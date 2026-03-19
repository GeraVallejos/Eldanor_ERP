from rest_framework import serializers

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


# ─── Pedido de Venta ──────────────────────────────────────────────────────────

class PedidoVentaSerializer(serializers.ModelSerializer):
    tiene_guias = serializers.SerializerMethodField()
    tiene_facturas = serializers.SerializerMethodField()
    cliente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = PedidoVenta
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "numero",
            "estado",
            "subtotal",
            "impuestos",
            "total",
            "tiene_guias",
            "tiene_facturas",
            "cliente_nombre",
        ]

    def get_tiene_guias(self, obj):
        return obj.guias_despacho.exists()

    def get_tiene_facturas(self, obj):
        return obj.facturas_venta.exists()

    def get_cliente_nombre(self, obj):
        try:
            return obj.cliente.contacto.nombre
        except Exception:
            return None

    def validate(self, data):
        if "fecha_entrega" in data and "fecha_emision" in data:
            if data["fecha_entrega"] and data["fecha_emision"]:
                if data["fecha_entrega"] < data["fecha_emision"]:
                    raise serializers.ValidationError(
                        {"fecha_entrega": "La fecha de entrega no puede ser anterior a la emisión."}
                    )
        return data


class PedidoVentaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidoVentaItem
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "subtotal",
            "total",
        ]


# ─── Guía de Despacho ─────────────────────────────────────────────────────────

class GuiaDespachoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = GuiaDespacho
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "numero",
            "estado",
            "subtotal",
            "impuestos",
            "total",
            "confirmado_por",
            "confirmado_en",
            "anulado_por",
            "anulado_en",
            "cliente_nombre",
        ]

    def get_cliente_nombre(self, obj):
        try:
            return obj.cliente.contacto.nombre
        except Exception:
            return None


class GuiaDespachoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuiaDespachoItem
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "subtotal",
            "total",
        ]


# ─── Factura de Venta ─────────────────────────────────────────────────────────

class FacturaVentaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.SerializerMethodField()
    auditoria_ultima = serializers.SerializerMethodField()

    class Meta:
        model = FacturaVenta
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "numero",
            "estado",
            "subtotal",
            "impuestos",
            "total",
            "emitido_por",
            "emitido_en",
            "anulado_por",
            "anulado_en",
            "cliente_nombre",
            "auditoria_ultima",
        ]

    def get_cliente_nombre(self, obj):
        try:
            return obj.cliente.contacto.nombre
        except Exception:
            return None

    def get_auditoria_ultima(self, obj):
        from apps.ventas.models import TipoDocumentoVenta
        ultimo = (
            VentaHistorial.all_objects.filter(
                tipo_documento=TipoDocumentoVenta.FACTURA,
                documento_id=obj.id,
            )
            .order_by("-creado_en")
            .first()
        )
        if not ultimo:
            return None
        usuario_nombre = None
        if ultimo.usuario_id:
            try:
                usuario_nombre = ultimo.usuario.get_full_name() or ultimo.usuario.username
            except Exception:
                pass
        return {
            "estado_nuevo": ultimo.estado_nuevo,
            "creado_en": ultimo.creado_en,
            "usuario": usuario_nombre,
        }

    def validate(self, data):
        fecha_emision = data.get("fecha_emision")
        fecha_vencimiento = data.get("fecha_vencimiento")
        if fecha_emision and fecha_vencimiento and fecha_vencimiento < fecha_emision:
            raise serializers.ValidationError(
                {"fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la emisión."}
            )
        return data


class FacturaVentaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacturaVentaItem
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "subtotal",
            "total",
        ]


# ─── Nota de Crédito de Venta ─────────────────────────────────────────────────

class NotaCreditoVentaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.SerializerMethodField()

    class Meta:
        model = NotaCreditoVenta
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "numero",
            "estado",
            "subtotal",
            "impuestos",
            "total",
            "emitido_por",
            "emitido_en",
            "anulado_por",
            "anulado_en",
            "cliente_nombre",
        ]

    def get_cliente_nombre(self, obj):
        try:
            return obj.cliente.contacto.nombre
        except Exception:
            return None

    def validate(self, data):
        factura_origen = data.get("factura_origen")
        if factura_origen:
            from apps.ventas.models import EstadoFacturaVenta
            if factura_origen.estado != EstadoFacturaVenta.EMITIDA:
                raise serializers.ValidationError(
                    {"factura_origen": "La factura de origen debe estar en estado EMITIDA."}
                )
        return data


class NotaCreditoVentaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaCreditoVentaItem
        fields = "__all__"
        read_only_fields = [
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "subtotal",
            "total",
        ]


# ─── Historial ────────────────────────────────────────────────────────────────

class VentaHistorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = VentaHistorial
        fields = "__all__"
        read_only_fields = ["id", "empresa", "creado_por", "creado_en"]
