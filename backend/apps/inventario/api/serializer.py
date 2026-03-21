from rest_framework import serializers

from apps.inventario.models import Bodega, InventorySnapshot, MovimientoInventario, StockProducto


class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class StockProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockProducto
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class InventorySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventorySnapshot
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class RegularizacionInventarioSerializer(serializers.Serializer):
    producto_id = serializers.UUIDField()
    bodega_id = serializers.UUIDField(required=False, allow_null=True)
    stock_objetivo = serializers.DecimalField(max_digits=12, decimal_places=2)
    referencia = serializers.CharField(max_length=150)
    costo_unitario = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        required=False,
        allow_null=True,
    )
    lote_codigo = serializers.CharField(max_length=80, required=False, allow_blank=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    series = serializers.ListField(
        child=serializers.CharField(max_length=80),
        required=False,
        allow_empty=True,
    )


class PrevisualizacionRegularizacionSerializer(serializers.Serializer):
    producto_id = serializers.UUIDField()
    bodega_id = serializers.UUIDField(required=False, allow_null=True)
    stock_objetivo = serializers.DecimalField(max_digits=12, decimal_places=2)


class TrasladoInventarioSerializer(serializers.Serializer):
    producto_id = serializers.UUIDField()
    bodega_origen_id = serializers.UUIDField()
    bodega_destino_id = serializers.UUIDField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2)
    referencia = serializers.CharField(max_length=150)
    lote_codigo = serializers.CharField(max_length=80, required=False, allow_blank=True)
