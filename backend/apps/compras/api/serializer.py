from rest_framework import serializers

from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    OrdenCompra,
    OrdenCompraItem,
)


class OrdenCompraSerializer(serializers.ModelSerializer):
    tiene_documentos = serializers.SerializerMethodField()
    tiene_documentos_activos = serializers.SerializerMethodField()

    class Meta:
        model = OrdenCompra
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en", "numero")
        validators = []

    def get_tiene_documentos(self, obj):
        return obj.documentos_compra.exists()

    def get_tiene_documentos_activos(self, obj):
        return obj.documentos_compra.exclude(estado=EstadoDocumentoCompra.ANULADO).exists()


class OrdenCompraItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenCompraItem
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class DocumentoCompraProveedorSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        request = self.context.get("request")
        empresa = (
            attrs.get("empresa")
            or getattr(self.instance, "empresa", None)
            or getattr(getattr(request, "user", None), "empresa_activa", None)
        )
        proveedor = attrs.get("proveedor") or getattr(self.instance, "proveedor", None)
        orden_compra = attrs.get("orden_compra") or getattr(self.instance, "orden_compra", None)
        estado = attrs.get("estado") or getattr(self.instance, "estado", EstadoDocumentoCompra.BORRADOR)

        if orden_compra and proveedor and orden_compra.proveedor_id != proveedor.id:
            raise serializers.ValidationError(
                {"orden_compra": "La orden de compra seleccionada no pertenece al proveedor indicado."}
            )

        if empresa and orden_compra and estado != EstadoDocumentoCompra.ANULADO:
            existentes = DocumentoCompraProveedor.all_objects.filter(
                empresa=empresa,
                orden_compra=orden_compra,
            ).exclude(estado=EstadoDocumentoCompra.ANULADO)

            if self.instance:
                existentes = existentes.exclude(pk=self.instance.pk)

            if existentes.exists():
                raise serializers.ValidationError(
                    {"orden_compra": "La orden de compra ya fue utilizada en otro documento activo."}
                )

        return attrs

    class Meta:
        model = DocumentoCompraProveedor
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class DocumentoCompraProveedorItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoCompraProveedorItem
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")
