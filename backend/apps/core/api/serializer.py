from rest_framework import serializers
from apps.core.models.empresa import Empresa



class EmpresaUsuarioSerializer(serializers.ModelSerializer):
    es_activa = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = ["id", "nombre", "rut", "es_activa"]

    def get_es_activa(self, obj):
        user = self.context["request"].user
        return user.empresa_activa_id == obj.id
    
    
class CambiarEmpresaActivaSerializer(serializers.Serializer):
    empresa_id = serializers.UUIDField()