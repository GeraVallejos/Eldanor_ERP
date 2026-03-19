from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.services import CarteraService, DomainEventService, OutboxService, SecuenciaService
from apps.core.services.accounting_bridge import AccountingBridge
from apps.core.models import TipoDocumento
from apps.core.models.cartera import CuentaPorCobrar
from apps.documentos.models import EstadoContable
from apps.documentos.services.integracion_tributaria_service import IntegracionTributariaService
from apps.ventas.models import (
    EstadoFacturaVenta,
    EstadoNotaCreditoVenta,
    FacturaVentaItem,
    NotaCreditoVenta,
    NotaCreditoVentaItem,
    TipoDocumentoVenta,
    TipoNotaCreditoVenta,
    VentaHistorial,
)
from apps.ventas.services.calculo_ventas_service import CalculoVentasService


class NotaCreditoVentaService:
    """Servicio para la gestión de notas de crédito de venta y su impacto en cartera."""

    @classmethod
    def recalcular_totales(cls, *, nota):
        """Recalcula subtotal, impuestos y total sumando items de la nota de crédito."""
        items_qs = NotaCreditoVentaItem.all_objects.filter(nota_credito=nota)
        CalculoVentasService.recalcular_documento(documento=nota, items_qs=items_qs)

    @classmethod
    def validar_editable(cls, *, nota):
        """Lanza ConflictError si la nota de crédito no está en estado BORRADOR."""
        if nota.estado != EstadoNotaCreditoVenta.BORRADOR:
            raise ConflictError("Solo se puede modificar una nota de crédito en estado BORRADOR.")

    @classmethod
    @transaction.atomic
    def crear_nota_credito(cls, *, datos, empresa, usuario):
        """Crea nota de crédito de venta con folio secuencial. Requiere factura origen EMITIDA."""
        factura_origen_id = datos.get("factura_origen_id") or (
            datos.get("factura_origen") and datos["factura_origen"].id
        )
        if not factura_origen_id:
            raise BusinessRuleError("Se requiere una factura de origen para crear una nota de crédito.")

        from apps.ventas.models import FacturaVenta
        factura = FacturaVenta.objects.filter(pk=factura_origen_id, empresa=empresa).first()
        if not factura:
            raise ResourceNotFoundError("Factura de venta de origen no encontrada.")
        if factura.estado != EstadoFacturaVenta.EMITIDA:
            raise ConflictError("Solo se puede crear nota de crédito sobre facturas EMITIDAS.")

        MAX_REINTENTOS = 5
        for intento in range(MAX_REINTENTOS):
            try:
                numero = SecuenciaService.obtener_siguiente_numero(
                    empresa, TipoDocumento.NOTA_CREDITO_VENTA
                )
                nota = NotaCreditoVenta.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    numero=numero,
                    **datos,
                )
                return nota
            except IntegrityError:
                if intento == MAX_REINTENTOS - 1:
                    raise
        raise BusinessRuleError("No se pudo asignar folio a la nota de crédito.")

    @classmethod
    @transaction.atomic
    def crear_nota_credito_anulacion(cls, *, factura, empresa, usuario, motivo=""):
        """
        Genera NC de anulación automática al anular una factura.
        Copia todos los items de la factura y emite la NC inmediatamente.
        """
        MAX_REINTENTOS = 5
        for intento in range(MAX_REINTENTOS):
            try:
                numero = SecuenciaService.obtener_siguiente_numero(
                    empresa, TipoDocumento.NOTA_CREDITO_VENTA
                )
                nota = NotaCreditoVenta.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    numero=numero,
                    factura_origen=factura,
                    cliente=factura.cliente,
                    tipo=TipoNotaCreditoVenta.ANULACION,
                    estado=EstadoNotaCreditoVenta.BORRADOR,
                    fecha_emision=factura.fecha_emision,
                    motivo=motivo or f"Anulación de factura {factura.numero}",
                )
                break
            except IntegrityError:
                if intento == MAX_REINTENTOS - 1:
                    raise

        # Copiar items de la factura hacia la NC.
        for item in FacturaVentaItem.all_objects.filter(factura_venta=factura):
            NotaCreditoVentaItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                nota_credito=nota,
                factura_item=item,
                producto_id=item.producto_id,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                impuesto_id=item.impuesto_id,
                impuesto_porcentaje=item.impuesto_porcentaje,
            )

        cls.recalcular_totales(nota=nota)
        cls.emitir_nota_credito(nota_id=nota.id, empresa=empresa, usuario=usuario)
        return nota

    @classmethod
    @transaction.atomic
    def emitir_nota_credito(cls, *, nota_id, empresa, usuario):
        """
        Emite nota de crédito BORRADOR→EMITIDA.
        Aplica el monto como pago contra la CxC asociada a la factura origen.
        No puede exceder el saldo pendiente de la CxC.
        """
        nota = (
            NotaCreditoVenta.objects.select_for_update().filter(pk=nota_id, empresa=empresa).first()
        )
        if not nota:
            raise ResourceNotFoundError("Nota de crédito de venta no encontrada.")
        if nota.estado != EstadoNotaCreditoVenta.BORRADOR:
            raise ConflictError(
                f"Solo se puede emitir una nota de crédito en BORRADOR (estado: {nota.get_estado_display()})."
            )
        if Decimal(nota.total or 0) <= 0:
            raise BusinessRuleError("No se puede emitir una nota de crédito con total cero.")

        items = NotaCreditoVentaItem.all_objects.filter(nota_credito=nota)
        if not items.exists():
            raise BusinessRuleError("No se puede emitir una nota de crédito sin líneas.")

        # Buscar la CxC correspondiente a la factura origen para aplicar el crédito.
        referencia_cxc = f"FV-{nota.factura_origen.numero}-{str(nota.factura_origen_id)[:8]}"
        cxc = CuentaPorCobrar.all_objects.filter(
            empresa=empresa,
            referencia=referencia_cxc,
        ).first()

        if cxc and Decimal(cxc.saldo or 0) > 0:
            monto_aplicar = min(Decimal(nota.total), Decimal(cxc.saldo))
            CarteraService.aplicar_pago_cuenta(
                cuenta=cxc,
                monto=monto_aplicar,
                fecha_pago=nota.fecha_emision,
            )

        estado_anterior = nota.estado
        nota.estado = EstadoNotaCreditoVenta.EMITIDA
        nota.emitido_por = usuario
        nota.emitido_en = timezone.now()
        nota.save(update_fields=["estado", "emitido_por", "emitido_en"])
        AccountingBridge.request_entry(
            empresa=empresa,
            aggregate_type="NotaCreditoVenta",
            aggregate_id=nota.id,
            entry_payload={
                "fecha": str(nota.fecha_emision),
                "glosa": f"Nota de credito {nota.numero}",
                "referencia_tipo": "NOTA_CREDITO_VENTA",
                "movimientos": [
                    {"cuenta_codigo": "411100", "debe": str(nota.subtotal), "haber": "0"},
                    {"cuenta_codigo": "213100", "debe": str(nota.impuestos), "haber": "0"},
                    {"cuenta_codigo": "112100", "debe": "0", "haber": str(nota.total)},
                ],
            },
            usuario=usuario,
            dedup_key=f"ncv-accounting:{nota.id}:emitida",
        )
        nota.estado_contable = EstadoContable.PENDIENTE
        nota.save(update_fields=["estado_contable", "actualizado_en"])
        IntegracionTributariaService.solicitar_emision(
            documento=nota,
            usuario=usuario,
            tipo_documento="NOTA_CREDITO_VENTA",
            payload_extra={"cliente_id": str(nota.cliente_id)},
        )

        cls.registrar_historial(
            nota=nota,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoNotaCreditoVenta.EMITIDA,
        )
        return nota

    @classmethod
    @transaction.atomic
    def anular_nota_credito(cls, *, nota_id, empresa, usuario, motivo=""):
        """Anula nota de crédito EMITIDA→ANULADA. No revierte el crédito aplicado en cartera."""
        nota = (
            NotaCreditoVenta.objects.select_for_update().filter(pk=nota_id, empresa=empresa).first()
        )
        if not nota:
            raise ResourceNotFoundError("Nota de crédito de venta no encontrada.")
        if nota.estado != EstadoNotaCreditoVenta.EMITIDA:
            raise ConflictError(
                f"Solo se puede anular una nota de crédito EMITIDA (estado: {nota.get_estado_display()})."
            )

        estado_anterior = nota.estado
        nota.estado = EstadoNotaCreditoVenta.ANULADA
        nota.anulado_por = usuario
        nota.anulado_en = timezone.now()
        nota.save(update_fields=["estado", "anulado_por", "anulado_en"])

        cls.registrar_historial(
            nota=nota,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoNotaCreditoVenta.ANULADA,
            motivo=motivo,
        )
        return nota

    @classmethod
    def registrar_historial(cls, *, nota, usuario, estado_anterior, estado_nuevo, motivo="", cambios=None):
        """Registra cambio de estado en historial, DomainEvent y OutboxEvent."""
        from apps.auditoria.services import AuditoriaService

        VentaHistorial.all_objects.create(
            empresa=nota.empresa,
            creado_por=usuario,
            tipo_documento=TipoDocumentoVenta.NOTA_CREDITO,
            documento_id=nota.id,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            motivo=motivo or "",
            cambios=cambios,
        )

        ikey = f"nc-{nota.id}-{estado_nuevo}"

        DomainEventService.record_event(
            empresa=nota.empresa,
            aggregate_type="NotaCreditoVenta",
            aggregate_id=nota.id,
            event_type=f"nota_credito_venta.{estado_nuevo.lower()}",
            payload={
                "nota_id": str(nota.id),
                "numero": nota.numero,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "factura_origen_id": str(nota.factura_origen_id),
            },
            meta={},
            idempotency_key=ikey,
            usuario=usuario,
        )

        OutboxService.enqueue(
            empresa=nota.empresa,
            topic="ventas.nota_credito",
            event_name=f"nota_credito_venta.{estado_nuevo.lower()}",
            payload={
                "nota_id": str(nota.id),
                "numero": nota.numero,
                "cliente_id": str(nota.cliente_id),
                "total": str(nota.total),
                "factura_origen_id": str(nota.factura_origen_id),
            },
            usuario=usuario,
            dedup_key=ikey,
        )

        AuditoriaService.registrar_evento(
            empresa=nota.empresa,
            usuario=usuario,
            module_code="VENTAS",
            action_code=estado_nuevo,
            event_type="nota_credito_venta.cambio_estado",
            entity_type="NotaCreditoVenta",
            entity_id=str(nota.id),
            summary=f"NC {nota.numero}: {estado_anterior} → {estado_nuevo}",
            changes=cambios,
        )
