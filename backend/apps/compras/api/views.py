from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.compras.api.serializer import (
    DocumentoCompraProveedorItemSerializer,
    DocumentoCompraProveedorSerializer,
    OrdenCompraItemSerializer,
    OrdenCompraSerializer,
    RecepcionCompraItemSerializer,
    RecepcionCompraSerializer,
)
from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    OrdenCompra,
    OrdenCompraItem,
    EstadoRecepcion,
    RecepcionCompra,
    RecepcionCompraItem,
)
from apps.compras.services import DocumentoCompraService, OrdenCompraService, RecepcionCompraService
from apps.core.exceptions import AuthorizationError, ConflictError
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.core.models import TipoDocumento
from apps.core.services import SecuenciaService


class OrdenCompraViewSet(TenantViewSetMixin, ModelViewSet):
    model = OrdenCompra
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "siguiente_numero": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "enviar": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "eliminar_sin_documentos": Acciones.BORRAR,
        "corregir": Acciones.EDITAR,
        "duplicar": Acciones.CREAR,
    }

    @staticmethod
    def _is_numero_oc_unique_error(error):
        message = str(error).lower()
        return (
            "unique_numero_oc_por_empresa" in message
            or "already exists" in message and "numero" in message and "empresa" in message
            or "ya existe" in message and "numero" in message and "empresa" in message
            or ("ordencompra" in message and "numero" in message and "empresa" in message)
            or ("orden compra" in message and "numero" in message and "empresa" in message)
        )

    def perform_update(self, serializer):
        self._set_tenant_context()
        OrdenCompraService.validar_orden_editable(orden=self.get_object())
        serializer.save()

    def perform_create(self, serializer):
        """Asigna numero secuencial y reintenta si encuentra uno ya ocupado."""
        max_attempts = 5
        for _ in range(max_attempts):
            numero_siguiente = SecuenciaService.obtener_siguiente_numero(
                empresa=self.request.user.empresa_activa,
                tipo_documento=TipoDocumento.ORDEN_COMPRA,
            )
            try:
                serializer.save(
                    numero=numero_siguiente,
                    empresa=self.request.user.empresa_activa,
                    creado_por=self.request.user,
                    estado="BORRADOR",
                )
                return
            except (IntegrityError, DjangoValidationError, DRFValidationError) as exc:
                if self._is_numero_oc_unique_error(exc):
                    continue
                raise

        raise ConflictError(
            "No fue posible asignar un numero de orden disponible. Intente nuevamente."
        )

    @action(detail=False, methods=["get"])
    def siguiente_numero(self, request):
        numero = SecuenciaService.obtener_numero_siguiente_disponible(
            empresa=request.user.empresa_activa,
            tipo_documento=TipoDocumento.ORDEN_COMPRA,
        )
        return Response({"numero": numero}, status=status.HTTP_200_OK)

    def enviar(self, request, pk=None):
        orden = OrdenCompraService.enviar_orden(orden_id=pk, empresa=request.user.empresa_activa)
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        orden = OrdenCompraService.anular_orden(orden_id=pk, empresa=request.user.empresa_activa)
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def eliminar_sin_documentos(self, request, pk=None):
        OrdenCompraService.eliminar_orden_sin_documentos(orden_id=pk, empresa=request.user.empresa_activa)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def corregir(self, request, pk=None):
        motivo = request.data.get("motivo")
        orden = OrdenCompraService.corregir_orden(
            orden_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            motivo=motivo,
        )
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        orden = OrdenCompraService.duplicar_orden(
            orden_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
        )
        serializer = self.get_serializer(orden)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrdenCompraItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = OrdenCompraItem
    serializer_class = OrdenCompraItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    def _get_orden_from_request_or_instance(self, instance=None):
        if instance is not None:
            return instance.orden_compra
        orden_id = self.request.data.get("orden_compra")
        if not orden_id:
            return None
        return OrdenCompra.all_objects.filter(id=orden_id, empresa=self.request.user.empresa_activa).first()

    def perform_create(self, serializer):
        self._set_tenant_context()
        orden = self._get_orden_from_request_or_instance()
        if orden:
            OrdenCompraService.validar_orden_editable(orden=orden)
        item = serializer.save()
        OrdenCompraService.recalcular_totales(orden=item.orden_compra)

    def perform_update(self, serializer):
        self._set_tenant_context()
        OrdenCompraService.validar_orden_editable(orden=self.get_object().orden_compra)
        item = serializer.save()
        OrdenCompraService.recalcular_totales(orden=item.orden_compra)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        OrdenCompraService.validar_orden_editable(orden=instance.orden_compra)
        orden = instance.orden_compra
        instance.delete()
        OrdenCompraService.recalcular_totales(orden=orden)


class DocumentoCompraProveedorViewSet(TenantViewSetMixin, ModelViewSet):
    model = DocumentoCompraProveedor
    serializer_class = DocumentoCompraProveedorSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar_guia": Acciones.APROBAR,
        "confirmar_factura": Acciones.APROBAR,
        "anular": Acciones.ANULAR,
        "corregir": Acciones.EDITAR,
        "duplicar": Acciones.CREAR,
    }

    def perform_update(self, serializer):
        self._set_tenant_context()
        DocumentoCompraService.validar_documento_editable(documento=self.get_object())
        serializer.save()

    def perform_create(self, serializer):
        self._set_tenant_context()
        instance = serializer.save(estado=EstadoDocumentoCompra.BORRADOR)
        DocumentoCompraService.avanzar_orden_si_borrador(documento=instance)
        DocumentoCompraService.recalcular_totales(documento=instance)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        DocumentoCompraService.validar_documento_editable(documento=instance)
        instance.delete()

    @action(detail=True, methods=["post"])
    def confirmar_guia(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        documento = DocumentoCompraService.confirmar_guia(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def confirmar_factura(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        documento = DocumentoCompraService.confirmar_factura(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        documento = DocumentoCompraService.anular_documento(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def corregir(self, request, pk=None):
        bodega_id = request.data.get("bodega_id")
        motivo = request.data.get("motivo")
        documento = DocumentoCompraService.corregir_documento(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            motivo=motivo,
            bodega_id=bodega_id,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def duplicar(self, request, pk=None):
        documento = DocumentoCompraService.duplicar_documento(
            documento_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
        )
        serializer = self.get_serializer(documento)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DocumentoCompraProveedorItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = DocumentoCompraProveedorItem
    serializer_class = DocumentoCompraProveedorItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        documento_id = self.request.query_params.get("documento")
        if documento_id:
            queryset = queryset.filter(documento_id=documento_id)
        return queryset

    def perform_create(self, serializer):
        self._set_tenant_context()
        documento = serializer.validated_data["documento"]
        empresa_id = getattr(self.request.user.empresa_activa, "id", None)
        if empresa_id and documento.empresa_id != empresa_id:
            raise AuthorizationError("No tiene permisos sobre el documento seleccionado.")
        if documento.estado != EstadoDocumentoCompra.BORRADOR:
            raise ConflictError("Solo se pueden agregar items en documentos en borrador.")
        item = serializer.save()
        DocumentoCompraService.recalcular_totales(documento=item.documento)

    def perform_update(self, serializer):
        self._set_tenant_context()
        documento = serializer.instance.documento
        empresa_id = getattr(self.request.user.empresa_activa, "id", None)
        if empresa_id and documento.empresa_id != empresa_id:
            raise AuthorizationError("No tiene permisos sobre el documento seleccionado.")
        if documento.estado != EstadoDocumentoCompra.BORRADOR:
            raise ConflictError("Solo se pueden editar items en documentos en borrador.")
        item = serializer.save()
        DocumentoCompraService.recalcular_totales(documento=item.documento)

    def perform_destroy(self, instance):
        self._set_tenant_context()
        if instance.documento.estado != EstadoDocumentoCompra.BORRADOR:
            raise ConflictError("Solo se pueden eliminar items en documentos en borrador.")
        documento = instance.documento
        instance.delete()
        DocumentoCompraService.recalcular_totales(documento=documento)


class RecepcionCompraViewSet(TenantViewSetMixin, ModelViewSet):
    model = RecepcionCompra
    serializer_class = RecepcionCompraSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar": Acciones.APROBAR,
    }

    def perform_create(self, serializer):
        self._set_tenant_context()
        serializer.save(estado=EstadoRecepcion.BORRADOR)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        recepcion = RecepcionCompraService.confirmar_recepcion(
            recepcion_id=pk,
            empresa=request.user.empresa_activa,
            usuario=request.user,
            bodega_id=request.data.get("bodega_id"),
        )
        serializer = self.get_serializer(recepcion)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecepcionCompraItemViewSet(TenantViewSetMixin, ModelViewSet):
    model = RecepcionCompraItem
    serializer_class = RecepcionCompraItemSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.COMPRAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
    }

    def perform_create(self, serializer):
        self._set_tenant_context()
        recepcion = serializer.validated_data["recepcion"]
        if recepcion.estado != EstadoRecepcion.BORRADOR:
            raise ConflictError("Solo se pueden agregar items en recepciones en borrador.")
        orden_item = serializer.validated_data.get("orden_item")
        if recepcion.orden_compra_id and not orden_item:
            raise ConflictError("Debe indicar orden_item cuando la recepcion esta asociada a una OC.")
        if orden_item and recepcion.orden_compra_id and orden_item.orden_compra_id != recepcion.orden_compra_id:
            raise ConflictError("El orden_item no pertenece a la OC de la recepcion.")
        serializer.save()

    def perform_update(self, serializer):
        self._set_tenant_context()
        if serializer.instance.recepcion.estado != EstadoRecepcion.BORRADOR:
            raise ConflictError("Solo se pueden editar items en recepciones en borrador.")
        serializer.save()

    def perform_destroy(self, instance):
        self._set_tenant_context()
        if instance.recepcion.estado != EstadoRecepcion.BORRADOR:
            raise ConflictError("Solo se pueden eliminar items en recepciones en borrador.")
        instance.delete()
