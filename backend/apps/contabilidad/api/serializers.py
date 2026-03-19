from rest_framework import serializers

from apps.contabilidad.models import AsientoContable, MovimientoContable, PlanCuenta


class PlanCuentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCuenta
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class MovimientoContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoContable
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en", "asiento")


class AsientoMovimientoInputSerializer(serializers.Serializer):
    cuenta = serializers.UUIDField()
    glosa = serializers.CharField(required=False, allow_blank=True, max_length=255)
    debe = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    haber = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)


class AsientoContableSerializer(serializers.ModelSerializer):
    movimientos = MovimientoContableSerializer(many=True, read_only=True)
    movimientos_data = AsientoMovimientoInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = AsientoContable
        fields = "__all__"
        read_only_fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "numero",
            "estado",
            "origen",
            "total_debe",
            "total_haber",
            "cuadrado",
        )

    def validate_movimientos_data(self, value):
        if not value:
            raise serializers.ValidationError("Debe informar al menos una linea contable.")
        return value
