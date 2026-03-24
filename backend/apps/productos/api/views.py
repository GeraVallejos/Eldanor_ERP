from datetime import date

from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import ValidationError

from apps.core.roles import RolUsuario
from apps.productos.models import Categoria, Impuesto, ListaPrecio, ListaPrecioItem, Producto
from apps.productos.api.serializer import (
    CategoriaSerializer,
    ImpuestoSerializer,
    ListaPrecioItemSerializer,
    ListaPrecioSerializer,
    ProductoHistorialSerializer,
    ProductoSerializer,
    ProductoVersionSerializer,
)
from apps.auditoria.services import AuditoriaService
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.permissions import TieneRelacionActiva, TienePermisoModuloAccion
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse
from django.utils.dateparse import parse_date

from apps.productos.services.bulk_import_service import bulk_import_productos, build_productos_bulk_template
from apps.productos.services.catalogo_service import CategoriaService, ImpuestoService
from apps.productos.services.lista_precio_bulk_import_service import (
    build_lista_precio_bulk_template,
    bulk_import_lista_precio_items,
)
from apps.productos.services.lista_precio_service import ListaPrecioItemService, ListaPrecioService
from apps.productos.services.precio_service import PrecioComercialService
from apps.productos.models import ProductoSnapshot
from apps.productos.services.producto_gobernanza_service import ProductoGobernanzaService
from apps.productos.services.producto_snapshot_service import ProductoSnapshotService
from apps.productos.services.producto_service import ProductoService
from apps.productos.services.producto_trazabilidad_service import ProductoTrazabilidadService


class ProductoHistorialPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductoListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ListaPrecioItemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


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
        "historial": Acciones.VER,
        "versiones": Acciones.VER,
        "gobernanza": Acciones.VER,
        "comparar_versiones": Acciones.VER,
        "restaurar_version": Acciones.EDITAR,
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
        queryset = super().get_queryset().select_related("categoria", "impuesto", "moneda")
        search_query = str(self.request.query_params.get("q") or "").strip()
        tipo_query = str(self.request.query_params.get("tipo") or "").strip().upper()
        categoria_query = str(self.request.query_params.get("categoria") or "").strip()
        has_explicit_pagination = bool(
            self.request.query_params.get("page") or self.request.query_params.get("page_size")
        )
        limit_query = self.request.query_params.get("limit")
        try:
            limit = min(max(int(limit_query), 1), 200) if limit_query is not None else None
        except (TypeError, ValueError):
            limit = None

        # En acciones de detalle permitimos acceder a inactivos para roles avanzados,
        # evitando 404 al reactivar productos previamente anulados.
        if self.action in {"retrieve", "update", "partial_update", "destroy", "precio", "trazabilidad", "historial", "versiones", "gobernanza", "comparar_versiones", "restaurar_version"}:
            if self._user_can_access_inactive():
                return queryset
            return queryset.filter(activo=True)

        include_inactive = self._is_truthy(self.request.query_params.get("include_inactive"))

        if not include_inactive:
            base_queryset = queryset.filter(activo=True)
        elif self._user_can_access_inactive():
            base_queryset = queryset
        else:
            base_queryset = queryset.filter(activo=True)

        if search_query:
            base_queryset = base_queryset.filter(
                Q(nombre__icontains=search_query) | Q(sku__icontains=search_query)
            )

        if tipo_query:
            base_queryset = base_queryset.filter(tipo=tipo_query)

        if categoria_query == "SIN_CATEGORIA":
            base_queryset = base_queryset.filter(categoria__isnull=True)
        elif categoria_query:
            base_queryset = base_queryset.filter(categoria_id=categoria_query)

        if limit is not None:
            return base_queryset.order_by("nombre")[:limit]

        if search_query and not has_explicit_pagination:
            return base_queryset.order_by("nombre")[:50]

        return base_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).order_by("nombre")

        # Conservamos compatibilidad con consumidores antiguos que esperan una lista plana
        # cuando no solicitan paginacion explicita.
        if request.query_params.get("page") or request.query_params.get("page_size"):
            paginator = ProductoListPagination()
            page = paginator.paginate_queryset(queryset, request, view=self)
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
            dry_run=self._is_truthy(request.data.get("dry_run")),
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

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()
        queryset = AuditoriaService.consultar_eventos(
            empresa=self.get_empresa(),
            module_code=Modulos.PRODUCTOS,
            entity_type="PRODUCTO",
            entity_id=producto.id,
        )
        paginator = ProductoHistorialPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductoHistorialSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="gobernanza")
    def gobernanza(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()
        payload = ProductoGobernanzaService.evaluar_producto(
            empresa=self.get_empresa(),
            producto=producto,
        )
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="versiones")
    def versiones(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()
        queryset = (
            ProductoSnapshot.all_objects
            .select_related("creado_por", "producto")
            .filter(empresa=self.get_empresa(), producto_id_ref=producto.id)
            .order_by("-version", "-creado_en")
        )
        paginator = ProductoHistorialPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ProductoVersionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"], url_path="versiones/comparar")
    def comparar_versiones(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()
        try:
            version_desde = int(request.query_params.get("version_desde") or "")
            version_hasta = int(request.query_params.get("version_hasta") or "")
        except (TypeError, ValueError) as exc:
            raise ValidationError({"detail": "Debe indicar version_desde y version_hasta validas."}) from exc

        payload = ProductoSnapshotService.comparar_versiones(
            empresa=self.get_empresa(),
            producto_id=producto.id,
            version_desde=version_desde,
            version_hasta=version_hasta,
        )
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="versiones/restaurar")
    def restaurar_version(self, request, pk=None):
        self._set_tenant_context()
        producto = self.get_object()
        try:
            version = int(request.data.get("version"))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"detail": "Debe indicar una version valida para restaurar."}) from exc

        result = ProductoSnapshotService.restaurar_version(
            empresa=self.get_empresa(),
            usuario=request.user,
            producto_id=producto.id,
            version=version,
        )
        response_serializer = self.get_serializer(result["producto"])
        return Response(
            {
                "version_restaurada": result["version_restaurada"],
                "producto": response_serializer.data,
            }
        )


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

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        categoria = CategoriaService.crear_categoria(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(categoria)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        categoria = CategoriaService.actualizar_categoria(
            categoria_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(categoria).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        CategoriaService.eliminar_categoria(
            categoria_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        impuesto = ImpuestoService.crear_impuesto(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(impuesto)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        impuesto = ImpuestoService.actualizar_impuesto(
            impuesto_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(impuesto).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ImpuestoService.eliminar_impuesto(
            impuesto_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        "bulk_import": Acciones.EDITAR,
        "bulk_template": Acciones.VER,
    }

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    def get_queryset(self):
        return super().get_queryset().select_related("moneda", "cliente__contacto")

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lista = ListaPrecioService.crear_lista(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(lista)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        lista = ListaPrecioService.actualizar_lista(
            lista_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(lista).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ListaPrecioService.eliminar_lista(
            lista_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request, pk=None):
        self._set_tenant_context()
        lista = self.get_object()
        payload = bulk_import_lista_precio_items(
            lista_id=lista.id,
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
            dry_run=self._is_truthy(request.data.get("dry_run")),
        )
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request, pk=None):
        self._set_tenant_context()
        lista = self.get_object()
        content = build_lista_precio_bulk_template(
            user=request.user,
            empresa=self.get_empresa(),
            lista_id=lista.id,
        )
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="plantilla_lista_{lista.id}.xlsx"'
        return response


class ListaPrecioItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = ListaPrecioItem
    serializer_class = ListaPrecioItemSerializer
    pagination_class = ListaPrecioItemPagination
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

    def get_queryset(self):
        queryset = super().get_queryset().select_related("lista", "producto").order_by("producto__nombre", "id")
        lista_id = self.request.query_params.get("lista")
        search_query = str(self.request.query_params.get("q") or "").strip()
        if lista_id:
            queryset = queryset.filter(lista_id=lista_id)
        if search_query:
            queryset = queryset.filter(
                Q(producto__nombre__icontains=search_query) | Q(producto__sku__icontains=search_query)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        self._set_tenant_context()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = ListaPrecioItemService.crear_item(
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        response_serializer = self.get_serializer(item)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        self._set_tenant_context()
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        item = ListaPrecioItemService.actualizar_item(
            item_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
            data=serializer.validated_data,
        )
        return Response(self.get_serializer(item).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._set_tenant_context()
        instance = self.get_object()
        ListaPrecioItemService.eliminar_item(
            item_id=instance.id,
            empresa=self.get_empresa(),
            usuario=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
