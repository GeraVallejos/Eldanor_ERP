from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from apps.contactos.models import Contacto, Cliente, Proveedor, CuentaBancaria, Direccion
from apps.contactos.api.serializer import (
    ContactoSerializer,
    ContactoTerceroDetailSerializer,
    ClienteSerializer,
    ClienteListSerializer,
    ClienteEditDetailSerializer,
    ProveedorSerializer,
    ProveedorListSerializer,
    ProveedorEditDetailSerializer,
    CuentaBancariaSerializer,
    DireccionSerializer,
    ClienteCreateWithContactoSerializer,
    ProveedorCreateWithContactoSerializer,
)
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from apps.core.roles import RolUsuario
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse

from apps.auditoria.api.serializer import AuditEventSerializer
from apps.auditoria.services import AuditoriaService
from apps.contactos.services.bulk_import_service import (
    import_clientes,
    import_proveedores,
    build_clientes_bulk_template,
    build_proveedores_bulk_template,
)
from apps.contactos.services.contacto_service import (
    ClienteService,
    ContactoService,
    CuentaBancariaService,
    DireccionService,
    ProveedorService,
)


class ContactosInactiveFilterMixin:
    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def _can_view_inactive(self):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return True

        empresa = self.get_empresa()
        if not empresa:
            return False

        rol = user.get_rol_en_empresa(empresa)
        return rol in {RolUsuario.OWNER, RolUsuario.ADMIN}

    def _should_include_inactive(self):
        include_inactive = self._is_truthy(self.request.query_params.get("include_inactive"))
        return include_inactive and self._can_view_inactive()

class ContactoViewSet(ContactosInactiveFilterMixin, TenantViewSetMixin, ModelViewSet):
    model = Contacto
    serializer_class = ContactoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "detalle_tercero": Acciones.VER,
        "auditoria": Acciones.VER,
        "create": Acciones.CREAR,
        "crear_con_contacto": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "bulk_import": Acciones.CREAR,
        "bulk_template": Acciones.VER,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset
        if self._should_include_inactive():
            return queryset
        return queryset.filter(activo=True)

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contacto = ContactoService.crear_contacto(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(contacto)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        contacto = ContactoService.actualizar_contacto(
            contacto_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(contacto).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ContactoService.eliminar_contacto(
            contacto_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="detalle-tercero")
    def detalle_tercero(self, request, pk=None):
        self._set_tenant_context()
        instance = self.get_object()
        contacto = (
            self.get_queryset()
            .select_related("cliente", "proveedor")
            .prefetch_related("direcciones", "cuentas_bancarias")
            .get(pk=instance.pk)
        )
        serializer = ContactoTerceroDetailSerializer(contacto)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="auditoria")
    def auditoria(self, request, pk=None):
        self._set_tenant_context()
        instance = self.get_object()
        contacto = (
            self.get_queryset()
            .select_related("cliente", "proveedor")
            .prefetch_related("direcciones", "cuentas_bancarias")
            .get(pk=instance.pk)
        )

        entity_refs = [("CONTACTO", contacto.id)]
        if getattr(contacto, "cliente", None):
            entity_refs.append(("CLIENTE", contacto.cliente.id))
        if getattr(contacto, "proveedor", None):
            entity_refs.append(("PROVEEDOR", contacto.proveedor.id))
        entity_refs.extend(("DIRECCION", direccion.id) for direccion in contacto.direcciones.all())
        entity_refs.extend(("CUENTA_BANCARIA", cuenta.id) for cuenta in contacto.cuentas_bancarias.all())

        eventos = AuditoriaService.consultar_eventos_por_entidades(
            empresa=self.get_empresa(),
            entities=entity_refs,
            limit=request.query_params.get("limit", 8),
        )
        serializer = AuditEventSerializer(eventos, many=True)
        return Response(serializer.data)


class ClienteViewSet(ContactosInactiveFilterMixin, TenantViewSetMixin, ModelViewSet):
    model = Cliente
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "detalle_edicion": Acciones.VER,
        "actualizar_con_contacto": Acciones.EDITAR,
        "create": Acciones.CREAR,
        "crear_con_contacto": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "bulk_import": Acciones.CREAR,
        "bulk_template": Acciones.VER,
    }

    def get_serializer_class(self):
        if self.action == "list":
            return ClienteListSerializer
        if self.action == "detalle_edicion":
            return ClienteEditDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset().select_related("contacto")
        if self.action != "list":
            return queryset
        if self._should_include_inactive():
            return queryset
        return queryset.filter(contacto__activo=True)

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cliente = ClienteService.crear_cliente(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(cliente)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=["post"], url_path="crear-con-contacto")
    def crear_con_contacto(self, request):
        self._set_tenant_context()
        serializer = ClienteCreateWithContactoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cliente = ClienteService.crear_cliente_con_contacto(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(cliente)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        cliente = ClienteService.actualizar_cliente(
            cliente_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(cliente).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ClienteService.eliminar_cliente(
            cliente_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="detalle-edicion")
    def detalle_edicion(self, request, pk=None):
        self._set_tenant_context()
        instance = self.get_object()
        cliente = self.get_queryset().select_related("contacto").get(pk=instance.pk)
        serializer = self.get_serializer(cliente)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="actualizar-con-contacto")
    def actualizar_con_contacto(self, request, pk=None):
        self._set_tenant_context()
        instance = self.get_object()
        serializer = ClienteCreateWithContactoSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        cliente = ClienteService.actualizar_cliente_con_contacto(
            cliente_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = ClienteEditDetailSerializer(cliente)
        return Response(response_serializer.data)

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        self._set_tenant_context()
        payload = import_clientes(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
            dry_run=self._is_truthy(request.data.get("dry_run")),
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        self._set_tenant_context()
        content = build_clientes_bulk_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_clientes.xlsx"'
        return response


class ProveedorViewSet(ContactosInactiveFilterMixin, TenantViewSetMixin, ModelViewSet):
    model = Proveedor
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.CONTACTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "detalle_edicion": Acciones.VER,
        "actualizar_con_contacto": Acciones.EDITAR,
        "create": Acciones.CREAR,
        "crear_con_contacto": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "bulk_import": Acciones.CREAR,
        "bulk_template": Acciones.VER,
    }

    def get_serializer_class(self):
        if self.action == "list":
            return ProveedorListSerializer
        if self.action == "detalle_edicion":
            return ProveedorEditDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset().select_related("contacto")
        if self.action != "list":
            return queryset
        if self._should_include_inactive():
            return queryset
        return queryset.filter(contacto__activo=True)

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proveedor = ProveedorService.crear_proveedor(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(proveedor)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=["post"], url_path="crear-con-contacto")
    def crear_con_contacto(self, request):
        self._set_tenant_context()
        serializer = ProveedorCreateWithContactoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proveedor = ProveedorService.crear_proveedor_con_contacto(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(proveedor)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        proveedor = ProveedorService.actualizar_proveedor(
            proveedor_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(proveedor).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ProveedorService.eliminar_proveedor(
            proveedor_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="detalle-edicion")
    def detalle_edicion(self, request, pk=None):
        self._set_tenant_context()
        instance = self.get_object()
        proveedor = self.get_queryset().select_related("contacto").get(pk=instance.pk)
        serializer = self.get_serializer(proveedor)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="actualizar-con-contacto")
    def actualizar_con_contacto(self, request, pk=None):
        self._set_tenant_context()
        instance = self.get_object()
        serializer = ProveedorCreateWithContactoSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        proveedor = ProveedorService.actualizar_proveedor_con_contacto(
            proveedor_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = ProveedorEditDetailSerializer(proveedor)
        return Response(response_serializer.data)

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        self._set_tenant_context()
        payload = import_proveedores(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
            dry_run=self._is_truthy(request.data.get("dry_run")),
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        self._set_tenant_context()
        content = build_proveedores_bulk_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_proveedores.xlsx"'
        return response


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

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cuenta = CuentaBancariaService.crear_cuenta(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(cuenta)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        cuenta = CuentaBancariaService.actualizar_cuenta(
            cuenta_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(cuenta).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        CuentaBancariaService.eliminar_cuenta(
            cuenta_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        direccion = DireccionService.crear_direccion(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(direccion)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        direccion = DireccionService.actualizar_direccion(
            direccion_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(direccion).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        DireccionService.eliminar_direccion(
            direccion_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
