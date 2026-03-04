from rest_framework import serializers
from apps.presupuestos.models import Presupuesto

class PresupuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Presupuesto
        fields = '__all__'
        read_only_fields = ('id', 'empresa', 'creado_por', 'numero', 'subtotal', 'total', 'impuesto_total')