from rest_framework import serializers
from apps.presupuestos.models import Presupuesto, PresupuestoItem


class PresupuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Presupuesto
        fields = '__all__'
        read_only_fields = (
            'id',
            'empresa',
            'creado_por',
            'numero',
            'estado',
            'subtotal',
            'impuesto_total',
            'total',
        )

class PresupuestoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresupuestoItem
        fields = "__all__"
        read_only_fields = ("empresa", "creado_por")
