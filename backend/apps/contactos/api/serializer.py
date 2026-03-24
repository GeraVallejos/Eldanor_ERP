from rest_framework import serializers
from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.contactos.models.cuentaBancaria import CuentaBancaria
from apps.contactos.models.direccion import Direccion
from apps.contactos.models.proveedor import Proveedor


class ContactoSerializer(serializers.ModelSerializer):
    """Serializer de contactos con contrato estricto para datos maestros obligatorios."""

    class Meta:
        model = Contacto
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "nombre",
            "razon_social",
            "rut",
            "tipo",
            "email",
            "telefono",
            "celular",
            "activo",
            "notas",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en"]
        extra_kwargs = {
            "rut": {"required": True, "allow_null": False, "allow_blank": False},
            "email": {"required": True, "allow_null": False, "allow_blank": False},
            "tipo": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def validate(self, attrs):
        errors = {}

        rut = attrs.get("rut", getattr(self.instance, "rut", None))
        email = attrs.get("email", getattr(self.instance, "email", None))
        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))

        if not str(rut or "").strip():
            errors["rut"] = ["Este campo es obligatorio."]
        if not str(email or "").strip():
            errors["email"] = ["Este campo es obligatorio."]
        if not str(tipo or "").strip():
            errors["tipo"] = ["Este campo es obligatorio."]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class ContactoResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = [
            "id",
            "nombre",
            "rut",
            "email",
            "telefono",
            "celular",
            "activo",
        ]


class ContactoMasterDataSerializer(serializers.Serializer):
    nombre = serializers.CharField(required=True, allow_blank=False)
    razon_social = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    rut = serializers.CharField(required=True, allow_blank=False)
    tipo = serializers.ChoiceField(choices=Contacto._meta.get_field("tipo").choices, required=True)
    email = serializers.EmailField(required=True, allow_blank=False)
    telefono = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    celular = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notas = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    activo = serializers.BooleanField(required=False, default=True)


class ClienteCreateWithContactoSerializer(ContactoMasterDataSerializer):
    limite_credito = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    dias_credito = serializers.IntegerField(required=False, default=0)
    categoria_cliente = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    segmento = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ProveedorCreateWithContactoSerializer(ContactoMasterDataSerializer):
    giro = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    vendedor_contacto = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    dias_credito = serializers.IntegerField(required=False, default=0)


class ClienteSerializer(serializers.ModelSerializer):
    contacto_nombre = serializers.CharField(source="contacto.nombre", read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "contacto_nombre",
            "limite_credito",
            "dias_credito",
            "categoria_cliente",
            "segmento",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en", "contacto_nombre"]


class ClienteListSerializer(serializers.ModelSerializer):
    contacto_resumen = ContactoResumenSerializer(source="contacto", read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "limite_credito",
            "dias_credito",
            "categoria_cliente",
            "segmento",
            "contacto_resumen",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en", "contacto_resumen"]


class ClienteEditDetailSerializer(serializers.ModelSerializer):
    contacto = ContactoSerializer(read_only=True)

    class Meta:
        model = Cliente
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "limite_credito",
            "dias_credito",
            "categoria_cliente",
            "segmento",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en", "contacto"]


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "giro",
            "vendedor_contacto",
            "dias_credito",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en"]


class ProveedorListSerializer(serializers.ModelSerializer):
    contacto_resumen = ContactoResumenSerializer(source="contacto", read_only=True)

    class Meta:
        model = Proveedor
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "giro",
            "vendedor_contacto",
            "dias_credito",
            "contacto_resumen",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en", "contacto_resumen"]


class ProveedorEditDetailSerializer(serializers.ModelSerializer):
    contacto = ContactoSerializer(read_only=True)

    class Meta:
        model = Proveedor
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "giro",
            "vendedor_contacto",
            "dias_credito",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en", "contacto"]


class CuentaBancariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaBancaria
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "banco",
            "tipo_cuenta",
            "numero_cuenta",
            "titular",
            "rut_titular",
            "activa",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en"]

class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = [
            "id",
            "empresa",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "contacto",
            "tipo",
            "direccion",
            "comuna",
            "ciudad",
            "region",
            "pais",
        ]
        read_only_fields = ["id", "empresa", "creado_por", "creado_en", "actualizado_en"]


class ContactoTerceroDetailSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    proveedor = ProveedorSerializer(read_only=True)
    direcciones = DireccionSerializer(many=True, read_only=True)
    cuentas_bancarias = CuentaBancariaSerializer(many=True, read_only=True)

    class Meta:
        model = Contacto
        fields = [
            "id",
            "nombre",
            "razon_social",
            "rut",
            "tipo",
            "email",
            "telefono",
            "celular",
            "activo",
            "notas",
            "cliente",
            "proveedor",
            "direcciones",
            "cuentas_bancarias",
        ]
