from rest_framework.viewsets import ModelViewSet
from apps.contactos.models import Contacto, Cliente, Proveedor, CuentaBancaria, Direccion
from apps.contactos.api.serializer import ContactoSerializer, ClienteSerializer, ProveedorSerializer, CuentaBancariaSerializer, DireccionSerializer
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva
from rest_framework.permissions import IsAuthenticated


class ContactoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Contacto
    serializer_class = ContactoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva]


class ClienteViewSet(TenantViewSetMixin, ModelViewSet):
    model = Cliente
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva]


class ProveedorViewSet(TenantViewSetMixin, ModelViewSet):
    model = Proveedor
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva]


class CuentaBancariaViewSet(TenantViewSetMixin, ModelViewSet):
    model = CuentaBancaria
    serializer_class = CuentaBancariaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva]


class DireccionViewSet(TenantViewSetMixin, ModelViewSet):
    model = Direccion
    serializer_class = DireccionSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva]