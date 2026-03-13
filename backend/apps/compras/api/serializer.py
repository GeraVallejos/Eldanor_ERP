from rest_framework import serializers

from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    EstadoRecepcion,
    OrdenCompra,
    OrdenCompraItem,
    RecepcionCompra,
    RecepcionCompraItem,
)


class OrdenCompraSerializer(serializers.ModelSerializer):
    tiene_documentos = serializers.SerializerMethodField()
    tiene_documentos_activos = serializers.SerializerMethodField()

    class Meta:
        model = OrdenCompra
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en", "numero", "estado")
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

        tipo_documento = attrs.get("tipo_documento") or getattr(self.instance, "tipo_documento", None)
        folio = attrs.get("folio") or getattr(self.instance, "folio", None)
        serie = attrs.get("serie") if "serie" in attrs else getattr(self.instance, "serie", "")

        if empresa and proveedor and tipo_documento and folio is not None:
            duplicado = DocumentoCompraProveedor.all_objects.filter(
                empresa=empresa,
                proveedor=proveedor,
                tipo_documento=tipo_documento,
                folio=folio,
                serie=serie or "",
                bloquea_duplicado=True,
            )
            if self.instance:
                duplicado = duplicado.exclude(pk=self.instance.pk)

            if duplicado.exists():
                raise serializers.ValidationError(
                    {"folio": "Ya existe un documento con este folio/serie para el proveedor y tipo indicado."}
                )

        return attrs

    class Meta:
        model = DocumentoCompraProveedor
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en", "estado")
        validators = []


class DocumentoCompraProveedorItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoCompraProveedorItem
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")


class RecepcionCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecepcionCompra
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en", "estado")


class RecepcionCompraItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecepcionCompraItem
        fields = "__all__"
        read_only_fields = ("id", "empresa", "creado_por", "creado_en", "actualizado_en")
