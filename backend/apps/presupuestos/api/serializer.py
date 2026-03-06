from rest_framework import serializers
from apps.presupuestos.models import Presupuesto, PresupuestoItem


class PresupuestoSerializer(serializers.ModelSerializer):
    auditoria_ultima = serializers.SerializerMethodField()

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
            'auditoria_ultima',
        )

    def get_auditoria_ultima(self, obj):
        ultimo = (
            obj.historial.select_related('usuario')
            .order_by('-creado_en')
            .first()
        )

        if not ultimo:
            return None

        usuario_nombre = ''
        if ultimo.usuario:
            nombre = f"{ultimo.usuario.first_name or ''} {ultimo.usuario.last_name or ''}".strip()
            usuario_nombre = nombre or ultimo.usuario.email or ultimo.usuario.username

        return {
            'estado_anterior': ultimo.estado_anterior,
            'estado_nuevo': ultimo.estado_nuevo,
            'usuario': usuario_nombre,
            'creado_en': ultimo.creado_en,
        }

class PresupuestoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresupuestoItem
        fields = "__all__"
        read_only_fields = ("empresa", "creado_por")
