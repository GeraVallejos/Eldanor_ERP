from rest_framework import serializers
from apps.productos.models import Categoria, Impuesto, ListaPrecio, ListaPrecioItem, Producto


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    impuesto_nombre = serializers.CharField(source="impuesto.nombre", read_only=True)
    moneda_codigo = serializers.CharField(source="moneda.codigo", read_only=True)

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
        )
        read_only_fields = (
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "moneda_codigo",
            "cliente_nombre",
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
