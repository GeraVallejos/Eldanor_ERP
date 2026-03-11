from decimal import Decimal

from django.db.models.deletion import ProtectedError
from rest_framework.viewsets import ModelViewSet

from apps.core.exceptions import ConflictError
from apps.inventario.models import Bodega, StockProducto
from apps.core.roles import RolUsuario
from apps.productos.models import Producto, Categoria, Impuesto
from apps.productos.api.serializer import ImpuestoSerializer, ProductoSerializer, CategoriaSerializer
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.http import HttpResponse

from apps.productos.services.bulk_import_service import bulk_import_productos, build_productos_bulk_template



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
    }

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def get_queryset(self):
        queryset = super().get_queryset()
        include_inactive = self._is_truthy(self.request.query_params.get("include_inactive"))

        if not include_inactive:
            return queryset.filter(activo=True)

        user = self.request.user
        if getattr(user, "is_superuser", False):
            return queryset

        empresa = self.get_empresa()
        if not empresa:
            return queryset.filter(activo=True)

        rol = user.get_rol_en_empresa(empresa)
        if rol in {RolUsuario.OWNER, RolUsuario.ADMIN}:
            return queryset

        return queryset.filter(activo=True)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        try:
            instance.delete()
        except ProtectedError:
            if not instance.activo:
                raise ConflictError(
                    "El producto ya esta anulado y mantiene referencias historicas."
                )
            # Conserva integridad historica cuando el producto ya fue usado.
            instance.activo = False
            instance.save(skip_clean=True, update_fields=["activo"])

    def _sync_stock_producto(self, producto):
        empresa = self.get_empresa() or getattr(producto, "empresa", None)
        if not empresa or not producto:
            return

        if not producto.maneja_inventario:
            StockProducto.all_objects.filter(empresa=empresa, producto=producto).update(
                stock=Decimal("0"),
                valor_stock=Decimal("0"),
            )
            return

        bodega_default, _ = Bodega.all_objects.get_or_create(
            empresa=empresa,
            nombre="Principal",
            defaults={"activa": True, "creado_por": self.request.user},
        )

        stock = Decimal(producto.stock_actual or 0).quantize(Decimal("0.01"))
        valor_stock = (stock * Decimal(producto.precio_costo or 0)).quantize(Decimal("0.01"))

        stock_obj, _ = StockProducto.all_objects.get_or_create(
            empresa=empresa,
            producto=producto,
            bodega=bodega_default,
            defaults={
                "creado_por": self.request.user,
                "stock": stock,
                "valor_stock": valor_stock,
            },
        )

        if stock_obj.stock != stock or stock_obj.valor_stock != valor_stock:
            stock_obj.stock = stock
            stock_obj.valor_stock = valor_stock
            stock_obj.save(update_fields=["stock", "valor_stock"])

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._sync_stock_producto(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._sync_stock_producto(serializer.instance)

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
