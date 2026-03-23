from rest_framework import serializers
from apps.auditoria.models import AuditEvent
from apps.productos.models import Categoria, Impuesto, ListaPrecio, ListaPrecioItem, Producto, ProductoSnapshot


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    impuesto_nombre = serializers.CharField(source="impuesto.nombre", read_only=True)
    moneda_codigo = serializers.CharField(source="moneda.codigo", read_only=True)

    def validate(self, attrs):
        if self.instance is not None and "precio_costo" in attrs:
            raise serializers.ValidationError(
                {"precio_costo": ["El precio de costo no se puede editar desde el maestro. Use documentos o ajustes autorizados."]}
            )
        return super().validate(attrs)

    class Meta:
        model = Producto
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "nombre",
            "descripcion",
            "sku",
            "tipo",
            "categoria",
            "categoria_nombre",
            "impuesto",
            "impuesto_nombre",
            "moneda",
            "moneda_codigo",
            "precio_referencia",
            "precio_costo",
            "unidad_medida",
            "permite_decimales",
            "maneja_inventario",
            "stock_actual",
            "costo_promedio",
            "stock_minimo",
            "usa_lotes",
            "usa_series",
            "usa_vencimiento",
            "activo",
        )
        read_only_fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "categoria_nombre",
            "impuesto_nombre",
            "moneda_codigo",
            "stock_actual",
            "costo_promedio",
        )

    
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "nombre",
            "descripcion",
            "activa",
        )
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
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "nombre",
            "porcentaje",
            "activo",
        )
        read_only_fields = (
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
        )


class ListaPrecioSerializer(serializers.ModelSerializer):
    moneda_codigo = serializers.CharField(source="moneda.codigo", read_only=True)
    cliente_nombre = serializers.CharField(source="cliente.contacto.nombre", read_only=True)
    prioridad_label = serializers.SerializerMethodField()

    @staticmethod
    def get_prioridad_label(obj):
        prioridad = int(getattr(obj, "prioridad", 0) or 0)
        labels = {
            10: "Urgente",
            50: "Alta",
            100: "Normal",
            200: "Respaldo",
        }
        return labels.get(prioridad, f"Personalizada ({prioridad})")

    class Meta:
        model = ListaPrecio
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "nombre",
            "moneda",
            "moneda_codigo",
            "cliente",
            "cliente_nombre",
            "fecha_desde",
            "fecha_hasta",
            "activa",
            "prioridad",
            "prioridad_label",
        )
        read_only_fields = (
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "moneda_codigo",
            "cliente_nombre",
            "prioridad_label",
        )


class ListaPrecioItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    lista_nombre = serializers.CharField(source="lista.nombre", read_only=True)

    class Meta:
        model = ListaPrecioItem
        fields = (
            "id",
            "empresa",
            "creado_por",
            "creado_en",
            "actualizado_en",
            "lista",
            "lista_nombre",
            "producto",
            "producto_nombre",
            "precio",
            "descuento_maximo",
        )
        read_only_fields = (
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "producto_nombre",
            "lista_nombre",
        )


class ProductoHistorialSerializer(serializers.ModelSerializer):
    creado_por_email = serializers.EmailField(source="creado_por.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "action_code",
            "event_type",
            "severity",
            "summary",
            "changes",
            "payload",
            "creado_por",
            "creado_por_email",
            "occurred_at",
        )
        read_only_fields = fields


class ProductoVersionSerializer(serializers.ModelSerializer):
    creado_por_email = serializers.EmailField(source="creado_por.email", read_only=True)

    class Meta:
        model = ProductoSnapshot
        fields = (
            "id",
            "producto",
            "producto_id_ref",
            "version",
            "event_type",
            "changes",
            "snapshot",
            "creado_por",
            "creado_por_email",
            "creado_en",
        )
        read_only_fields = fields
