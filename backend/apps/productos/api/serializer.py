from rest_framework import serializers
from apps.productos.models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"
        read_only_fields = ("creado_por", "creado_en", "actualizado_en")

    def validate(self, data):
        user = self.context["request"].user
        
        # Obtenemos la categoría que viene en el request
        categoria = data.get('categoria')

        if not user.is_superuser:
            # 1. Forzamos la empresa del usuario
            data['empresa'] = user.empresa
            
            # 2. Validación de Categoria (Si viene una)
            if categoria:
                # Comparamos los IDs convertidos a string para evitar errores de tipo UUID vs String
                empresa_user_id = str(user.empresa.id)
                empresa_cat_id = str(categoria.empresa.id)
                
                if empresa_user_id != empresa_cat_id:
                    raise serializers.ValidationError({
                        "categoria": "El registro seleccionado de categoria no pertenece a su empresa."
                    })
        return data