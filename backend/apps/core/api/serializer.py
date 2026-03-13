from rest_framework import serializers
from apps.core.models.empresa import Empresa
from apps.core.models import CuentaPorCobrar, CuentaPorPagar, TipoCambio



class EmpresaUsuarioSerializer(serializers.ModelSerializer):
    es_activa = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = ["id", "nombre", "rut", "es_activa"]
        read_only_fields = ["empresa", "creado_por"]

    def get_es_activa(self, obj):
        user = self.context["request"].user
        return user.empresa_activa_id == obj.id
    
    
class CambiarEmpresaActivaSerializer(serializers.Serializer):
    empresa_id = serializers.UUIDField()


class GestionPermisosSerializer(serializers.Serializer):
    relacion_id = serializers.IntegerField(min_value=1)
    permisos = serializers.ListField(
        child=serializers.CharField(max_length=80),
        allow_empty=True,
    )


class UsuarioEmpresaPermisosSerializer(serializers.Serializer):
    relacion_id = serializers.IntegerField(min_value=1)
    user_id = serializers.UUIDField()
    email = serializers.EmailField()
    nombre = serializers.CharField()
    rol = serializers.CharField()
    permisos_personalizados = serializers.ListField(child=serializers.CharField())
    permisos_efectivos = serializers.ListField(child=serializers.CharField())


class PlantillaPermisosSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=60)
    nombre = serializers.CharField(max_length=120)
    descripcion = serializers.CharField(allow_blank=True, required=False)
    permisos = serializers.ListField(child=serializers.CharField(max_length=80), allow_empty=True)
    activa = serializers.BooleanField(required=False)


class AplicarPlantillaSerializer(serializers.Serializer):
    relacion_id = serializers.IntegerField(min_value=1)
    plantilla_codigo = serializers.CharField(max_length=60)


class TipoCambioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCambio
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


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