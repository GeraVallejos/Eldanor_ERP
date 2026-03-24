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
        fields = "__all__"
        read_only_fields = ["empresa", "creado_por"]
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


class ClienteSerializer(serializers.ModelSerializer):
    contacto_nombre = serializers.CharField(source='contacto.nombre', read_only=True)

    class Meta:
        model = Cliente
        fields = "__all__"
        read_only_fields = ["empresa", "creado_por"]

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"
        read_only_fields = ["empresa", "creado_por"]


class CuentaBancariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaBancaria
        fields = "__all__"
        read_only_fields = ["empresa", "creado_por"]

class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = "__all__"
        read_only_fields = ["empresa", "creado_por"]
