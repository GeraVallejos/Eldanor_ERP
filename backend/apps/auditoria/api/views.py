from datetime import datetime, time

from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.auditoria.api.serializer import AuditEventSerializer
from apps.auditoria.models import AuditEvent
from apps.auditoria.services import AuditoriaService
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.permissions import TienePermisoModuloAccion, TieneRelacionActiva


class AuditoriaPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = "page_size"
    max_page_size = 200


class AuditEventViewSet(TenantViewSetMixin, ReadOnlyModelViewSet):
    model = AuditEvent
    serializer_class = AuditEventSerializer
    pagination_class = AuditoriaPagination
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.AUDITORIA
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "integridad": Acciones.VER,
    }

    @staticmethod
    def _parse_instant(value, *, end_of_day=False):
        if not value:
            return None

        dt = parse_datetime(value)
        if dt is not None:
            return dt

        d = parse_date(value)
        if d is None:
            return None

        return datetime.combine(d, time.max if end_of_day else time.min)

    @staticmethod
    def _as_bool(value):
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "si", "sí"}

    def get_queryset(self):
        queryset = super().get_queryset()

        module_code = self.request.query_params.get("module_code")
        action_code = self.request.query_params.get("action_code")
        event_type = self.request.query_params.get("event_type")
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        severity = self.request.query_params.get("severity")
        created_by_id = self.request.query_params.get("created_by_id")
        date_from = self._parse_instant(self.request.query_params.get("date_from"))
        date_to = self._parse_instant(self.request.query_params.get("date_to"), end_of_day=True)

        return AuditoriaService.consultar_eventos(
            empresa=self.get_empresa(),
            module_code=module_code,
            action_code=action_code,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            created_by_id=created_by_id,
            date_from=date_from,
            date_to=date_to,
        )

    @action(detail=False, methods=["get"])
    def integridad(self, request):
        limit = request.query_params.get("limit")
        date_from = self._parse_instant(request.query_params.get("date_from"))
        date_to = self._parse_instant(request.query_params.get("date_to"), end_of_day=True)
        include_blocks = self._as_bool(request.query_params.get("resumen") or request.query_params.get("blocks"))
        block_size = request.query_params.get("block_size") or 1000

        result = AuditoriaService.verificar_cadena_integridad_avanzada(
            empresa=self.get_empresa(),
            limit=limit if limit not in (None, "") else None,
            date_from=date_from,
            date_to=date_to,
            include_blocks=include_blocks,
            block_size=block_size,
        )
        status_code = status.HTTP_200_OK if result["is_valid"] else status.HTTP_409_CONFLICT
        return Response(result, status=status_code)
