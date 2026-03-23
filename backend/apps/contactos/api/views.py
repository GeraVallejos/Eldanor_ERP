from rest_framework.viewsets import ModelViewSet
from apps.contactos.models import Contacto, Cliente, Proveedor, CuentaBancaria, Direccion
from apps.contactos.api.serializer import ContactoSerializer, ClienteSerializer, ProveedorSerializer, CuentaBancariaSerializer, DireccionSerializer
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from apps.core.roles import RolUsuario
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.http import HttpResponse
from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService

from apps.contactos.services.bulk_import_service import (
    import_clientes,
    import_proveedores,
    build_clientes_bulk_template,
    build_proveedores_bulk_template,
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


class ContactosAuditoriaMixin:
    @staticmethod
    def _serialize_changes(validated_data):
        changes = {}
        for key, value in (validated_data or {}).items():
            changes[key] = str(value) if value is not None else None
        return changes

    def _registrar_auditoria(self, *, instance, event_type, summary, action_code, severity=AuditSeverity.INFO, changes=None):
        empresa = self.get_empresa()
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=self.request.user,
            module_code=Modulos.CONTACTOS,
            action_code=action_code,
            event_type=event_type,
            entity_type=instance.__class__.__name__.upper(),
            entity_id=str(instance.id),
            summary=summary,
            severity=severity,
            changes=changes or {},
            payload={
                "model": instance.__class__.__name__,
                "empresa_id": str(getattr(instance, "empresa_id", "") or ""),
            },
            source="contactos.api.views",
        )


class ContactoViewSet(ContactosAuditoriaMixin, ContactosInactiveFilterMixin, TenantViewSetMixin, ModelViewSet ):
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

    def perform_create(self, serializer):
        self._set_tenant_context()
        instance = serializer.save()
        self._registrar_auditoria(
            instance=instance,
            event_type="CONTACTO_CREADO",
            summary=f"Contacto {instance.nombre} creado.",
            action_code=Acciones.CREAR,
            changes=self._serialize_changes(serializer.validated_data),
        )

    def perform_update(self, serializer):
        self._set_tenant_context()
        instance = serializer.save()
        self._registrar_auditoria(
            instance=instance,
            event_type="CONTACTO_ACTUALIZADO",
            summary=f"Contacto {instance.nombre} actualizado.",
            action_code=Acciones.EDITAR,
            changes=self._serialize_changes(serializer.validated_data),
        )

    def perform_destroy(self, instance):
        self._set_tenant_context()
        summary = f"Contacto {instance.nombre} eliminado."
        instance.delete()
        self._registrar_auditoria(
            instance=instance,
            event_type="CONTACTO_ELIMINADO",
            summary=summary,
            action_code=Acciones.BORRAR,
            severity=AuditSeverity.WARNING,
        )


class ClienteViewSet(ContactosAuditoriaMixin, ContactosInactiveFilterMixin, TenantViewSetMixin, ModelViewSet):
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
        "bulk_import": Acciones.CREAR,
        "bulk_template": Acciones.VER,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset
        if self._should_include_inactive():
            return queryset
        return queryset.filter(contacto__activo=True)

    def perform_create(self, serializer):
        self._set_tenant_context()
        instance = serializer.save()
        self._registrar_auditoria(
            instance=instance,
            event_type="CLIENTE_CREADO",
            summary=f"Cliente {instance.contacto.nombre} creado.",
            action_code=Acciones.CREAR,
            changes=self._serialize_changes(serializer.validated_data),
        )

    def perform_update(self, serializer):
        self._set_tenant_context()
        instance = serializer.save()
        self._registrar_auditoria(
            instance=instance,
            event_type="CLIENTE_ACTUALIZADO",
            summary=f"Cliente {instance.contacto.nombre} actualizado.",
            action_code=Acciones.EDITAR,
            changes=self._serialize_changes(serializer.validated_data),
        )

    def perform_destroy(self, instance):
        self._set_tenant_context()
        summary = f"Cliente {instance.contacto.nombre} eliminado."
        instance.delete()
        self._registrar_auditoria(
            instance=instance,
            event_type="CLIENTE_ELIMINADO",
            summary=summary,
            action_code=Acciones.BORRAR,
            severity=AuditSeverity.WARNING,
        )

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


class ProveedorViewSet(ContactosAuditoriaMixin, ContactosInactiveFilterMixin, TenantViewSetMixin, ModelViewSet):
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
        "bulk_import": Acciones.CREAR,
        "bulk_template": Acciones.VER,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset
        if self._should_include_inactive():
            return queryset
        return queryset.filter(contacto__activo=True)

    def perform_create(self, serializer):
        self._set_tenant_context()
        instance = serializer.save()
        self._registrar_auditoria(
            instance=instance,
            event_type="PROVEEDOR_CREADO",
            summary=f"Proveedor {instance.contacto.nombre} creado.",
            action_code=Acciones.CREAR,
            changes=self._serialize_changes(serializer.validated_data),
        )

    def perform_update(self, serializer):
        self._set_tenant_context()
        instance = serializer.save()
        self._registrar_auditoria(
            instance=instance,
            event_type="PROVEEDOR_ACTUALIZADO",
            summary=f"Proveedor {instance.contacto.nombre} actualizado.",
            action_code=Acciones.EDITAR,
            changes=self._serialize_changes(serializer.validated_data),
        )

    def perform_destroy(self, instance):
        self._set_tenant_context()
        summary = f"Proveedor {instance.contacto.nombre} eliminado."
        instance.delete()
        self._registrar_auditoria(
            instance=instance,
            event_type="PROVEEDOR_ELIMINADO",
            summary=summary,
            action_code=Acciones.BORRAR,
            severity=AuditSeverity.WARNING,
        )

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
