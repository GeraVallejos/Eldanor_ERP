from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.services import CarteraService, DomainEventService, OutboxService, SecuenciaService
from apps.core.models import TipoDocumento
from apps.documentos.services.integracion_tributaria_service import IntegracionTributariaService
from apps.ventas.models import (
    EstadoFacturaVenta,
    EstadoPedidoVenta,
    FacturaVenta,
    FacturaVentaItem,
    TipoDocumentoVenta,
    VentaHistorial,
)
from apps.ventas.services.calculo_ventas_service import CalculoVentasService


class FacturaVentaService:
    """Servicio para la gestión de facturas de venta y su integración con cartera."""

    @classmethod
    def recalcular_totales(cls, *, factura):
        """Recalcula subtotal, impuestos y total sumando items activos de la factura."""
        items_qs = FacturaVentaItem.all_objects.filter(factura_venta=factura)
        CalculoVentasService.recalcular_documento(documento=factura, items_qs=items_qs)

    @classmethod
    def validar_editable(cls, *, factura):
        """Lanza ConflictError si la factura no está en estado BORRADOR."""
        if factura.estado != EstadoFacturaVenta.BORRADOR:
            raise ConflictError("Solo se puede modificar una factura en estado BORRADOR.")

    @classmethod
    @transaction.atomic
    def crear_factura(cls, *, datos, empresa, usuario):
        """Crea factura de venta con folio secuencial. Puede vincularse a pedido o guía."""
        MAX_REINTENTOS = 5
        for intento in range(MAX_REINTENTOS):
            try:
                numero = SecuenciaService.obtener_siguiente_numero(empresa, TipoDocumento.FACTURA_VENTA)
                factura = FacturaVenta.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    numero=numero,
                    **datos,
                )
                return factura
            except IntegrityError:
                if intento == MAX_REINTENTOS - 1:
                    raise
        raise BusinessRuleError("No se pudo asignar folio a la factura de venta.")

    @classmethod
    @transaction.atomic
    def emitir_factura(cls, *, factura_id, empresa, usuario):
        """
        Emite factura BORRADOR→EMITIDA.
        Registra cuenta por cobrar en cartera usando días de crédito del cliente.
        Actualiza estado del pedido vinculado a FACTURADO si corresponde.
        """
        factura = (
            FacturaVenta.objects.select_for_update().filter(pk=factura_id, empresa=empresa).first()
        )
        if not factura:
            raise ResourceNotFoundError("Factura de venta no encontrada.")
        if factura.estado != EstadoFacturaVenta.BORRADOR:
            raise ConflictError(
                f"Solo se puede emitir una factura en BORRADOR (estado actual: {factura.get_estado_display()})."
            )
        if Decimal(factura.total or 0) <= 0:
            raise BusinessRuleError("No se puede emitir una factura con total cero o negativo.")

        items = FacturaVentaItem.all_objects.filter(factura_venta=factura)
        if not items.exists():
            raise BusinessRuleError("No se puede emitir una factura sin líneas.")

        estado_anterior = factura.estado
        factura.estado = EstadoFacturaVenta.EMITIDA
        factura.emitido_por = usuario
        factura.emitido_en = timezone.now()
        factura.save(update_fields=["estado", "emitido_por", "emitido_en"])
        IntegracionTributariaService.solicitar_emision(
            documento=factura,
            usuario=usuario,
            tipo_documento="FACTURA_VENTA",
            payload_extra={"cliente_id": str(factura.cliente_id)},
        )

        # Registrar cuenta por cobrar. Referencia única por empresa+numero de factura.
        referencia_cxc = f"FV-{factura.numero}-{str(factura.id)[:8]}"
        CarteraService.registrar_cxc_manual(
            empresa=empresa,
            cliente=factura.cliente,
            referencia=referencia_cxc,
            fecha_emision=factura.fecha_emision,
            fecha_vencimiento=factura.fecha_vencimiento,
            monto_total=factura.total,
            moneda=None,
            usuario=usuario,
        )

        # Marcar pedido vinculado como FACTURADO.
        if factura.pedido_venta_id:
            pedido = factura.pedido_venta
            if pedido.estado not in {EstadoPedidoVenta.ANULADO, EstadoPedidoVenta.FACTURADO}:
                pedido.estado = EstadoPedidoVenta.FACTURADO
                pedido.save(update_fields=["estado"])

        cls.registrar_historial(
            factura=factura,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoFacturaVenta.EMITIDA,
        )
        return factura

    @classmethod
    @transaction.atomic
    def anular_factura(cls, *, factura_id, empresa, usuario, motivo=""):
        """
        Anula factura EMITIDA→ANULADA. La cuenta por cobrar queda con saldo reducido
        a cero mediante una nota de crédito de anulación generada automáticamente.
        """
        from apps.ventas.services.nota_credito_venta_service import NotaCreditoVentaService

        factura = (
            FacturaVenta.objects.select_for_update().filter(pk=factura_id, empresa=empresa).first()
        )
        if not factura:
            raise ResourceNotFoundError("Factura de venta no encontrada.")
        if factura.estado != EstadoFacturaVenta.EMITIDA:
            raise ConflictError(
                f"Solo se puede anular una factura EMITIDA (estado actual: {factura.get_estado_display()})."
            )

        estado_anterior = factura.estado
        factura.estado = EstadoFacturaVenta.ANULADA
        factura.anulado_por = usuario
        factura.anulado_en = timezone.now()
        factura.save(update_fields=["estado", "anulado_por", "anulado_en"])

        cls.registrar_historial(
            factura=factura,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoFacturaVenta.ANULADA,
            motivo=motivo,
        )

        # Generar nota de crédito de anulación automática.
        NotaCreditoVentaService.crear_nota_credito_anulacion(
            factura=factura,
            empresa=empresa,
            usuario=usuario,
            motivo=motivo or f"Anulación de factura {factura.numero}",
        )

        return factura

    @classmethod
    def registrar_historial(cls, *, factura, usuario, estado_anterior, estado_nuevo, motivo="", cambios=None):
        """Registra cambio de estado en historial, DomainEvent y OutboxEvent."""
        from apps.auditoria.services import AuditoriaService

        VentaHistorial.all_objects.create(
            empresa=factura.empresa,
            creado_por=usuario,
            tipo_documento=TipoDocumentoVenta.FACTURA,
            documento_id=factura.id,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            motivo=motivo or "",
            cambios=cambios,
        )

        ikey = f"fv-{factura.id}-{estado_nuevo}"

        DomainEventService.record_event(
            empresa=factura.empresa,
            aggregate_type="FacturaVenta",
            aggregate_id=factura.id,
            event_type=f"factura_venta.{estado_nuevo.lower()}",
            payload={
                "factura_id": str(factura.id),
                "numero": factura.numero,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "motivo": motivo,
            },
            meta={},
            idempotency_key=ikey,
            usuario=usuario,
        )

        OutboxService.enqueue(
            empresa=factura.empresa,
            topic="ventas.factura",
            event_name=f"factura_venta.{estado_nuevo.lower()}",
            payload={
                "factura_id": str(factura.id),
                "numero": factura.numero,
                "cliente_id": str(factura.cliente_id),
                "total": str(factura.total),
            },
            usuario=usuario,
            dedup_key=ikey,
        )

        AuditoriaService.registrar_evento(
            empresa=factura.empresa,
            usuario=usuario,
            module_code="VENTAS",
            action_code=estado_nuevo,
            event_type="factura_venta.cambio_estado",
            entity_type="FacturaVenta",
            entity_id=str(factura.id),
            summary=f"Factura {factura.numero}: {estado_anterior} → {estado_nuevo}",
            changes=cambios,
        )
