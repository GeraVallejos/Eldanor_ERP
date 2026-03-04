from rest_framework.viewsets import ModelViewSet
from apps.contactos.models import Contacto, Cliente, Proveedor, CuentaBancaria, Direccion
from apps.contactos.api.serializer import ContactoSerializer, ClienteSerializer, ProveedorSerializer, CuentaBancariaSerializer, DireccionSerializer
from apps.core.mixins import TenantViewSetMixin


class ContactoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Contacto
    serializer_class = ContactoSerializer


class ClienteViewSet(TenantViewSetMixin, ModelViewSet):
    model = Cliente
    serializer_class = ClienteSerializer


class ProveedorViewSet(TenantViewSetMixin, ModelViewSet):
    model = Proveedor
    serializer_class = ProveedorSerializer


class CuentaBancariaViewSet(TenantViewSetMixin, ModelViewSet):
    model = CuentaBancaria
    serializer_class = CuentaBancariaSerializer


class DireccionViewSet(TenantViewSetMixin, ModelViewSet):
    model = Direccion
    serializer_class = DireccionSerializer