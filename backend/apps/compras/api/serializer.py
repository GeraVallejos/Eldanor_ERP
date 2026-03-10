from rest_framework import serializers

from apps.compras.models import OrdenCompra, OrdenCompraItem, RecepcionCompra, RecepcionCompraItem


class OrdenCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenCompra
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class OrdenCompraItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenCompraItem
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class RecepcionCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecepcionCompra
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class RecepcionCompraItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecepcionCompraItem
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")
