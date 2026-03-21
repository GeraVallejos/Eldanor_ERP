from rest_framework import serializers

from apps.tesoreria.models import (
    CuentaBancariaEmpresa,
    CuentaPorCobrar,
    CuentaPorPagar,
    Moneda,
    MovimientoBancario,
    TipoCambio,
)


class TipoCambioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCambio
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class CuentaBancariaEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaBancariaEmpresa
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class MovimientoBancarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoBancario
        fields = "__all__"
        read_only_fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "conciliado",
            "conciliado_en",
        )


class ConvertirMontoSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=14, decimal_places=2)
    moneda_origen = serializers.CharField(max_length=3)
    moneda_destino = serializers.CharField(max_length=3)
    fecha = serializers.DateField(required=False)
    decimales = serializers.IntegerField(required=False, min_value=0, max_value=6)


class CuentaPorCobrarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaPorCobrar
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class CuentaPorPagarSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaPorPagar
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class AplicarPagoSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=14, decimal_places=2)
    fecha_pago = serializers.DateField()


class ConciliarMovimientoBancarioSerializer(serializers.Serializer):
    cuenta_por_cobrar = serializers.UUIDField(required=False)
    cuenta_por_pagar = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if bool(attrs.get("cuenta_por_cobrar")) == bool(attrs.get("cuenta_por_pagar")):
            raise serializers.ValidationError(
                "Debe indicar una cuenta por cobrar o una cuenta por pagar."
            )
        return attrs

__all__ = [
    "AplicarPagoSerializer",
    "ConciliarMovimientoBancarioSerializer",
    "ConvertirMontoSerializer",
    "CuentaBancariaEmpresaSerializer",
    "CuentaPorCobrarSerializer",
    "CuentaPorPagarSerializer",
    "MonedaSerializer",
    "MovimientoBancarioSerializer",
    "TipoCambioSerializer",
]
