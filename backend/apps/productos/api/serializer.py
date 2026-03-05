from rest_framework import serializers
from apps.productos.models import Producto, Categoria, Impuesto


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"
        read_only_fields = ("empresa","creado_por", "creado_en", "actualizado_en")

    
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = "__all__"
        read_only_fields = (
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
        )


class ImpuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impuesto
        fields = "__all__"
        read_only_fields = (
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
        )