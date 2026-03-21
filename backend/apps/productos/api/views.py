from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.roles import RolUsuario
from apps.productos.models import Categoria, Impuesto, ListaPrecio, ListaPrecioItem, Producto
from apps.productos.api.serializer import (
    CategoriaSerializer,
    ImpuestoSerializer,
    ListaPrecioItemSerializer,
    ListaPrecioSerializer,
    ProductoSerializer,
)
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from django.utils.dateparse import parse_date

from apps.productos.services.bulk_import_service import bulk_import_productos, build_productos_bulk_template
from apps.productos.services.precio_service import PrecioComercialService
from apps.productos.services.producto_service import ProductoService
from apps.productos.services.producto_trazabilidad_service import ProductoTrazabilidadService



class ProductoViewSet(TenantViewSetMixin, ModelViewSet ):
    model = Producto
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "bulk_import": Acciones.CREAR,
        "bulk_template": Acciones.VER,
        "precio": Acciones.VER,
        "trazabilidad": Acciones.VER,
    }

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def _user_can_access_inactive(self):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return True

        empresa = self.get_empresa()
        if not empresa:
            return False

        rol = user.get_rol_en_empresa(empresa)
        return rol in {RolUsuario.OWNER, RolUsuario.ADMIN}

    def get_queryset(self):
        queryset = super().get_queryset()
        # En acciones de detalle permitimos acceder a inactivos para roles avanzados,
        # evitando 404 al reactivar productos previamente anulados.
        if self.action in {"retrieve", "update", "partial_update", "destroy", "precio", "trazabilidad"}:
            if self._user_can_access_inactive():
                return queryset
            return queryset.filter(activo=True)

        include_inactive = self._is_truthy(self.request.query_params.get("include_inactive"))

        if not include_inactive:
            return queryset.filter(activo=True)

        if self._user_can_access_inactive():
            return queryset

        return queryset.filter(activo=True)

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = ProductoService.crear_producto(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(producto)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        producto = ProductoService.actualizar_producto(
            producto_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(producto)
        return Response(response_serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ProductoService.eliminar_producto(
            producto_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        self._set_tenant_context()
        payload = bulk_import_productos(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
        )
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        self._set_tenant_context()
        content = build_productos_bulk_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_productos.xlsx"'
        return response

    @action(detail=True, methods=["get"], url_path="precio")
    def precio(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()

        cliente = None
        cliente_id = request.query_params.get("cliente_id")
        if cliente_id:
            from apps.contactos.models import Cliente

            cliente = Cliente.all_objects.filter(empresa=self.get_empresa(), id=cliente_id).first()

        moneda_destino = None
        moneda_codigo = request.query_params.get("moneda")
        if moneda_codigo:
            from apps.tesoreria.models import Moneda

            moneda_destino = Moneda.all_objects.filter(
                empresa=self.get_empresa(),
                codigo=str(moneda_codigo).strip().upper(),
            ).first()

        fecha = parse_date(request.query_params.get("fecha") or "") or date.today()

        resultado = PrecioComercialService.obtener_precio(
            empresa=self.get_empresa(),
            producto=producto,
            cliente=cliente,
            fecha=fecha,
            moneda_destino=moneda_destino,
        )
        return Response(
            {
                "producto_id": str(producto.id),
                "precio": resultado["precio"],
                "moneda": getattr(resultado["moneda"], "codigo", None),
                "fuente": resultado["fuente"],
                "lista_id": str(resultado["lista"].id) if resultado["lista"] else None,
            }
        )

    @action(detail=True, methods=["get"], url_path="trazabilidad")
    def trazabilidad(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()
        fecha = parse_date(request.query_params.get("fecha") or "") or date.today()
        payload = ProductoTrazabilidadService.obtener_resumen(
            empresa=self.get_empresa(),
            producto=producto,
            fecha=fecha,
        )
        return Response(payload)


class CategoriaViewSet(TenantViewSetMixin, ModelViewSet):
    model = Categoria
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class ImpuestoViewSet(TenantViewSetMixin, ModelViewSet):
    model = Impuesto
    serializer_class = ImpuestoSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class ListaPrecioViewSet(TenantViewSetMixin, ModelViewSet):
    model = ListaPrecio
    serializer_class = ListaPrecioSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }


class ListaPrecioItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = ListaPrecioItem
    serializer_class = ListaPrecioItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.PRODUCTOS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }
