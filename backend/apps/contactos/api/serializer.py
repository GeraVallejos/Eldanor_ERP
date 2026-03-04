from rest_framework import serializers
from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.contactos.models.cuentaBancaria import CuentaBancaria
from apps.contactos.models.direccion import Direccion
from apps.contactos.models.proveedor import Proveedor


class ContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = "__all__"


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"


class CuentaBancariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaBancaria
        fields = "__all__"

class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = "__all__"