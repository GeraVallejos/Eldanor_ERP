from rest_framework import serializers

from apps.contabilidad.models import (
    AsientoContable,
    ConfiguracionCuentaContable,
    MovimientoContable,
    PlanCuenta,
)


class PlanCuentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanCuenta
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class ConfiguracionCuentaContableSerializer(serializers.ModelSerializer):
    cuenta_codigo = serializers.CharField(source="cuenta.codigo", read_only=True)
    cuenta_nombre = serializers.CharField(source="cuenta.nombre", read_only=True)

    class Meta:
        model = ConfiguracionCuentaContable
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en", "cuenta_codigo", "cuenta_nombre")


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


class OutboxContableErrorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    aggregate_type = serializers.CharField()
    aggregate_id = serializers.CharField()
    glosa = serializers.CharField(allow_blank=True)
    error = serializers.CharField(allow_blank=True)
    attempts = serializers.IntegerField()
    available_at = serializers.DateTimeField()


class ReporteMayorSerializer(serializers.Serializer):
    cuenta_id = serializers.CharField()
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    debe = serializers.DecimalField(max_digits=14, decimal_places=2)
    haber = serializers.DecimalField(max_digits=14, decimal_places=2)
    saldo = serializers.DecimalField(max_digits=14, decimal_places=2)


class EstadoResultadosSerializer(serializers.Serializer):
    ingresos = ReporteMayorSerializer(many=True)
    gastos = ReporteMayorSerializer(many=True)
    total_ingresos = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_gastos = serializers.DecimalField(max_digits=14, decimal_places=2)
    utilidad = serializers.DecimalField(max_digits=14, decimal_places=2)
