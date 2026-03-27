from rest_framework import serializers

from apps.inventario.models import (
    AjusteInventarioMasivo,
    AjusteInventarioMasivoItem,
    Bodega,
    EstadoDocumentoInventario,
    InventorySnapshot,
    MovimientoInventario,
    StockLote,
    StockSerie,
    StockProducto,
    TrasladoInventarioMasivo,
    TrasladoInventarioMasivoItem,
)


class BodegaSerializer(serializers.ModelSerializer):
    tiene_uso_historico = serializers.SerializerMethodField()

    def get_tiene_uso_historico(self, obj):
        annotated_flags = [
            getattr(obj, "has_movimientos", None),
            getattr(obj, "has_stocks", None),
            getattr(obj, "has_snapshots", None),
            getattr(obj, "has_reservas", None),
            getattr(obj, "has_stocks_lote", None),
            getattr(obj, "has_series", None),
        ]
        if any(value is not None for value in annotated_flags):
            return any(bool(value) for value in annotated_flags)

        return any(
            (
                obj.movimientos.exists(),
                obj.stocks.exists(),
                obj.snapshots_inventario.exists(),
                obj.reservas.exists(),
                obj.stocks_lote.exists(),
                obj.series.exists(),
            )
        )

    class Meta:
        model = Bodega
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "nombre",
            "activa",
            "tiene_uso_historico",
        )
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class StockProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockProducto
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "producto",
            "bodega",
            "stock",
            "valor_stock",
        )
        read_only_fields = fields


class StockLoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega.nombre", read_only=True)
    series_disponibles = serializers.SerializerMethodField()

    def get_series_disponibles(self, obj):
        return StockSerie.all_objects.filter(
            empresa=obj.empresa,
            producto=obj.producto,
            bodega=obj.bodega,
            lote_codigo=obj.lote_codigo,
            estado="DISPONIBLE",
        ).count()

    class Meta:
        model = StockLote
        fields = (
            "id",
            "producto",
            "producto_nombre",
            "bodega",
            "bodega_nombre",
            "lote_codigo",
            "fecha_vencimiento",
            "stock",
            "series_disponibles",
        )
        read_only_fields = fields


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "producto",
            "bodega",
            "tipo",
            "cantidad",
            "stock_anterior",
            "stock_nuevo",
            "costo_unitario",
            "valor_total",
            "lote_codigo",
            "fecha_vencimiento",
            "series_codigos",
            "documento_tipo",
            "documento_id",
            "referencia",
        )
        read_only_fields = fields


class InventorySnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventorySnapshot
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "producto",
            "bodega",
            "movimiento",
            "stock",
            "valor_stock",
            "costo_promedio",
        )
        read_only_fields = fields


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


class CorregirLoteSerializer(serializers.Serializer):
    nuevo_codigo = serializers.CharField(max_length=80)
    motivo = serializers.CharField(max_length=300)


class AnularLoteSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=300)


class AjusteInventarioMasivoItemCreateSerializer(serializers.Serializer):
    producto_id = serializers.UUIDField()
    bodega_id = serializers.UUIDField(required=False, allow_null=True)
    stock_objetivo = serializers.DecimalField(max_digits=12, decimal_places=2)
    lote_codigo = serializers.CharField(max_length=80, required=False, allow_blank=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)


class AjusteInventarioMasivoCreateSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=EstadoDocumentoInventario.choices,
        required=False,
        default=EstadoDocumentoInventario.CONFIRMADO,
    )
    referencia = serializers.CharField(max_length=150)
    motivo = serializers.CharField(max_length=120)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    items = AjusteInventarioMasivoItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe informar al menos una linea.")
        return value


class AjusteInventarioMasivoUpdateSerializer(serializers.Serializer):
    referencia = serializers.CharField(max_length=150, required=False)
    motivo = serializers.CharField(max_length=120, required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    items = AjusteInventarioMasivoItemCreateSerializer(many=True, required=False)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe informar al menos una linea.")
        return value


class AjusteInventarioMasivoItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    bodega_nombre = serializers.CharField(source="bodega.nombre", read_only=True)

    class Meta:
        model = AjusteInventarioMasivoItem
        fields = (
            "id",
            "producto",
            "producto_nombre",
            "bodega",
            "bodega_nombre",
            "stock_actual",
            "stock_objetivo",
            "lote_codigo",
            "fecha_vencimiento",
            "diferencia",
            "movimiento",
        )


class AjusteInventarioMasivoSerializer(serializers.ModelSerializer):
    items = AjusteInventarioMasivoItemSerializer(many=True, read_only=True)

    class Meta:
        model = AjusteInventarioMasivo
        fields = (
            "id",
            "numero",
            "estado",
            "referencia",
            "motivo",
            "observaciones",
            "subtotal",
            "total",
            "confirmado_en",
            "creado_en",
            "items",
        )


class TrasladoInventarioMasivoItemCreateSerializer(serializers.Serializer):
    producto_id = serializers.UUIDField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2)


class TrasladoInventarioMasivoCreateSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(
        choices=EstadoDocumentoInventario.choices,
        required=False,
        default=EstadoDocumentoInventario.CONFIRMADO,
    )
    referencia = serializers.CharField(max_length=150)
    motivo = serializers.CharField(max_length=120)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    bodega_origen_id = serializers.UUIDField()
    bodega_destino_id = serializers.UUIDField()
    items = TrasladoInventarioMasivoItemCreateSerializer(many=True)

    def validate(self, attrs):
        if str(attrs["bodega_origen_id"]) == str(attrs["bodega_destino_id"]):
            raise serializers.ValidationError({"bodega_destino_id": "La bodega destino debe ser distinta a la bodega origen."})
        if not attrs.get("items"):
            raise serializers.ValidationError({"items": "Debe informar al menos una linea."})
        return attrs


class TrasladoInventarioMasivoUpdateSerializer(serializers.Serializer):
    referencia = serializers.CharField(max_length=150, required=False)
    motivo = serializers.CharField(max_length=120, required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    bodega_origen_id = serializers.UUIDField(required=False)
    bodega_destino_id = serializers.UUIDField(required=False)
    items = TrasladoInventarioMasivoItemCreateSerializer(many=True, required=False)

    def validate(self, attrs):
        origen = attrs.get("bodega_origen_id")
        destino = attrs.get("bodega_destino_id")
        if origen and destino and str(origen) == str(destino):
            raise serializers.ValidationError({"bodega_destino_id": "La bodega destino debe ser distinta a la bodega origen."})
        if "items" in attrs and not attrs.get("items"):
            raise serializers.ValidationError({"items": "Debe informar al menos una linea."})
        return attrs


class TrasladoInventarioMasivoItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = TrasladoInventarioMasivoItem
        fields = (
            "id",
            "producto",
            "producto_nombre",
            "cantidad",
            "movimiento_salida",
            "movimiento_entrada",
        )


class TrasladoInventarioMasivoSerializer(serializers.ModelSerializer):
    items = TrasladoInventarioMasivoItemSerializer(many=True, read_only=True)
    bodega_origen_nombre = serializers.CharField(source="bodega_origen.nombre", read_only=True)
    bodega_destino_nombre = serializers.CharField(source="bodega_destino.nombre", read_only=True)

    class Meta:
        model = TrasladoInventarioMasivo
        fields = (
            "id",
            "numero",
            "estado",
            "referencia",
            "motivo",
            "observaciones",
            "bodega_origen",
            "bodega_origen_nombre",
            "bodega_destino",
            "bodega_destino_nombre",
            "subtotal",
            "total",
            "confirmado_en",
            "creado_en",
            "items",
        )
