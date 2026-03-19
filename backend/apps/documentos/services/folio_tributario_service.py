from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleError
from apps.core.models import (
    ConfiguracionTributaria,
    RangoFolioTributario,
    TipoDocumentoTributario,
)


class FolioTributarioService:
    """Administra configuracion tributaria y reserva segura de folios autorizados."""

    @staticmethod
    def obtener_configuracion_activa(*, empresa):
        """Retorna la configuracion tributaria activa de la empresa o levanta error de negocio."""
        config = ConfiguracionTributaria.all_objects.filter(
            empresa=empresa,
            activa=True,
        ).first()
        if not config:
            raise BusinessRuleError(
                "La empresa no tiene configuracion tributaria activa para operar con SII.",
                error_code="SII_CONFIG_MISSING",
            )
        return config

    @staticmethod
    @transaction.atomic
    def reservar_siguiente_folio(*, empresa, tipo_documento):
        """Reserva el siguiente folio disponible de un rango CAF vigente para el documento."""
        FolioTributarioService.obtener_configuracion_activa(empresa=empresa)

        hoy = timezone.localdate()
        rango = (
            RangoFolioTributario.all_objects
            .select_for_update()
            .filter(
                empresa=empresa,
                tipo_documento=tipo_documento,
                activo=True,
            )
            .order_by("fecha_vencimiento", "folio_desde")
            .first()
        )
        if not rango:
            raise BusinessRuleError(
                f"No existe un rango CAF activo para {tipo_documento}.",
                error_code="TRIBUTARY_FOLIO_UNAVAILABLE",
            )

        if rango.fecha_vencimiento and rango.fecha_vencimiento < hoy:
            raise BusinessRuleError(
                f"El rango CAF activo para {tipo_documento} esta vencido.",
                error_code="TRIBUTARY_FOLIO_EXPIRED",
            )

        siguiente = rango.folio_desde if rango.folio_actual is None else rango.folio_actual + 1
        if siguiente > rango.folio_hasta:
            raise BusinessRuleError(
                f"El rango CAF activo para {tipo_documento} no tiene folios disponibles.",
                error_code="TRIBUTARY_FOLIO_EXHAUSTED",
            )

        rango.folio_actual = siguiente
        rango.save(update_fields=["folio_actual", "actualizado_en"])
        return rango, str(siguiente)

    @staticmethod
    def normalizar_tipo_documento(*, tipo_documento):
        """Mapea identificadores de negocio a los tipos tributarios soportados."""
        mapping = {
            "FACTURA_VENTA": TipoDocumentoTributario.FACTURA_VENTA,
            "GUIA_DESPACHO": TipoDocumentoTributario.GUIA_DESPACHO,
            "NOTA_CREDITO_VENTA": TipoDocumentoTributario.NOTA_CREDITO_VENTA,
        }
        if tipo_documento not in mapping:
            raise BusinessRuleError(
                f"Tipo de documento tributario no soportado: {tipo_documento}.",
                error_code="TRIBUTARY_DOCUMENT_UNSUPPORTED",
            )
        return mapping[tipo_documento]
