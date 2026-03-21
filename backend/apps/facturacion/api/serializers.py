from rest_framework import serializers

from apps.facturacion.models import ConfiguracionTributaria, RangoFolioTributario


class ConfiguracionTributariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionTributaria
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class RangoFolioTributarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RangoFolioTributario
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")

