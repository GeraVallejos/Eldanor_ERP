from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva
from apps.facturacion.api.serializers import ConfiguracionTributariaSerializer, RangoFolioTributarioSerializer
from apps.facturacion.models import ConfiguracionTributaria, RangoFolioTributario
from apps.facturacion.services import build_rangos_folios_template, import_rangos_folios_tributarios


class ConfiguracionTributariaViewSet(TenantViewSetMixin, ModelViewSet):
    model = ConfiguracionTributaria
    serializer_class = ConfiguracionTributariaSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.FACTURACION
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.EDITAR,
    }


class RangoFolioTributarioViewSet(TenantViewSetMixin, ModelViewSet):
    model = RangoFolioTributario
    serializer_class = RangoFolioTributarioSerializer
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.FACTURACION
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.EDITAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.EDITAR,
        "bulk_import": Acciones.EDITAR,
        "bulk_template": Acciones.VER,
    }

    @staticmethod
    def _is_truthy(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "on"}

    @action(detail=False, methods=["post"], url_path="bulk_import", parser_classes=[MultiPartParser, FormParser])
    def bulk_import(self, request):
        self._set_tenant_context()
        payload = import_rangos_folios_tributarios(
            uploaded_file=request.FILES.get("file"),
            user=request.user,
            empresa=self.get_empresa(),
            dry_run=self._is_truthy(request.data.get("dry_run")),
        )
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="bulk_template")
    def bulk_template(self, request):
        self._set_tenant_context()
        content = build_rangos_folios_template(user=request.user, empresa=self.get_empresa())
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla_rangos_folios_sii.xlsx"'
        return response
