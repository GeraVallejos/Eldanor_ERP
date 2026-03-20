from rest_framework import serializers
from apps.presupuestos.models import Presupuesto, PresupuestoItem


class PresupuestoSerializer(serializers.ModelSerializer):
    auditoria_ultima = serializers.SerializerMethodField()
    estado_uso_comercial = serializers.SerializerMethodField()
    puede_generar_documentos = serializers.SerializerMethodField()
    resumen_comercial = serializers.SerializerMethodField()

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
            'estado_uso_comercial',
            'puede_generar_documentos',
            'resumen_comercial',
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

    def _get_resumen_comercial(self, obj):
        from apps.presupuestos.services.presupuesto_service import PresupuestoService

        cache_attr = "_resumen_comercial_cache"
        if not hasattr(obj, cache_attr):
            setattr(obj, cache_attr, PresupuestoService.resumen_consumo_comercial(presupuesto=obj))
        return getattr(obj, cache_attr)

    def get_estado_uso_comercial(self, obj):
        return self._get_resumen_comercial(obj)["estado_uso"]

    def get_puede_generar_documentos(self, obj):
        return self._get_resumen_comercial(obj)["puede_generar_documentos"]

    def get_resumen_comercial(self, obj):
        resumen = self._get_resumen_comercial(obj)
        return {
            "cantidad_total": resumen["cantidad_total"],
            "cantidad_usada": resumen["cantidad_usada"],
            "cantidad_disponible": resumen["cantidad_disponible"],
            "lineas_totales": resumen["lineas_totales"],
            "lineas_completas": resumen["lineas_completas"],
        }

class PresupuestoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresupuestoItem
        fields = "__all__"
        read_only_fields = ("empresa", "creado_por")
