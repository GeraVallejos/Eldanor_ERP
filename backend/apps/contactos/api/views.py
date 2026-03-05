from rest_framework.viewsets import ModelViewSet
from apps.contactos.models import Contacto, Cliente, Proveedor, CuentaBancaria, Direccion
from apps.contactos.api.serializer import ContactoSerializer, ClienteSerializer, ProveedorSerializer, CuentaBancariaSerializer, DireccionSerializer
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from rest_framework.permissions import IsAuthenticated


class ContactoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Contacto
    serializer_class = ContactoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class ClienteViewSet(TenantViewSetMixin, ModelViewSet):
    model = Cliente
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class ProveedorViewSet(TenantViewSetMixin, ModelViewSet):
    model = Proveedor
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class CuentaBancariaViewSet(TenantViewSetMixin, ModelViewSet):
    model = CuentaBancaria
    serializer_class = CuentaBancariaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class DireccionViewSet(TenantViewSetMixin, ModelViewSet):
    model = Direccion
    serializer_class = DireccionSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }
