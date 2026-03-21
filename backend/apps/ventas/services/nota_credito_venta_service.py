from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import TipoDocumento
from apps.core.services import DomainEventService, OutboxService, SecuenciaService
from apps.tesoreria.models import CuentaPorCobrar
from apps.tesoreria.services import CarteraService
from apps.core.services.accounting_bridge import AccountingBridge
from apps.documentos.models import EstadoContable, TipoDocumentoReferencia
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
    """Servicio para la gestion de notas de credito de venta y su impacto en cartera."""

    @classmethod
    def _registrar_reingreso_inventario_si_corresponde(cls, *, nota, items, empresa, usuario):
        """Registra reingreso fisico solo para notas de credito por devolucion."""
        from apps.inventario.services.inventario_service import InventarioService

        if nota.tipo != TipoNotaCreditoVenta.DEVOLUCION:
            return

        for item in items:
            if not item.producto_id or not item.producto.maneja_inventario:
                continue

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                tipo="ENTRADA",
                cantidad=item.cantidad,
                referencia=f"NCV-{nota.numero}",
                empresa=empresa,
                usuario=usuario,
                documento_tipo=TipoDocumentoReferencia.AJUSTE,
                documento_id=nota.id,
            )

    @classmethod
    def _revertir_reingreso_inventario_si_corresponde(cls, *, nota, empresa, usuario):
        """Revierte el reingreso fisico cuando se anula una devolucion ya emitida."""
        from apps.inventario.models import MovimientoInventario, TipoMovimiento
        from apps.inventario.services.inventario_service import InventarioService

        if nota.tipo != TipoNotaCreditoVenta.DEVOLUCION:
            return

        items = NotaCreditoVentaItem.all_objects.filter(nota_credito=nota).select_related("producto")
        for item in items:
            if not item.producto_id or not item.producto.maneja_inventario:
                continue

            movimiento_entrada = (
                MovimientoInventario.all_objects.filter(
                    empresa=empresa,
                    producto_id=item.producto_id,
                    documento_tipo=TipoDocumentoReferencia.AJUSTE,
                    documento_id=nota.id,
                    tipo=TipoMovimiento.ENTRADA,
                    referencia=f"NCV-{nota.numero}",
                )
                .order_by("-creado_en", "-id")
                .first()
            )
            if not movimiento_entrada:
                continue

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                bodega_id=movimiento_entrada.bodega_id,
                tipo=TipoMovimiento.SALIDA,
                cantidad=item.cantidad,
                referencia=f"ANULACION-NCV-{nota.numero}",
                empresa=empresa,
                usuario=usuario,
                costo_unitario=movimiento_entrada.costo_unitario,
                documento_tipo=TipoDocumentoReferencia.AJUSTE,
                documento_id=nota.id,
            )

    @classmethod
    def recalcular_totales(cls, *, nota):
        """Recalcula subtotal, impuestos y total sumando items de la nota de credito."""
        items_qs = NotaCreditoVentaItem.all_objects.filter(nota_credito=nota)
        CalculoVentasService.recalcular_documento(documento=nota, items_qs=items_qs)

    @classmethod
    def validar_editable(cls, *, nota):
        """Lanza ConflictError si la nota de credito no esta en estado BORRADOR."""
        if nota.estado != EstadoNotaCreditoVenta.BORRADOR:
            raise ConflictError("Solo se puede modificar una nota de credito en estado BORRADOR.")

    @classmethod
    @transaction.atomic
    def crear_nota_credito(cls, *, datos, empresa, usuario):
        """Crea nota de credito de venta con folio secuencial. Requiere factura origen EMITIDA."""
        factura_origen_id = datos.get("factura_origen_id") or (
            datos.get("factura_origen") and datos["factura_origen"].id
        )
        if not factura_origen_id:
            raise BusinessRuleError("Se requiere una factura de origen para crear una nota de credito.")

        from apps.ventas.models import FacturaVenta

        factura = FacturaVenta.objects.filter(pk=factura_origen_id, empresa=empresa).first()
        if not factura:
            raise ResourceNotFoundError("Factura de venta de origen no encontrada.")
        if factura.estado != EstadoFacturaVenta.EMITIDA:
            raise ConflictError("Solo se puede crear nota de credito sobre facturas EMITIDAS.")

        max_reintentos = 5
        for intento in range(max_reintentos):
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
                if intento == max_reintentos - 1:
                    raise
        raise BusinessRuleError("No se pudo asignar folio a la nota de credito.")

    @classmethod
    @transaction.atomic
    def crear_nota_credito_anulacion(cls, *, factura, empresa, usuario, motivo=""):
        """
        Genera NC de anulacion automatica al anular una factura.
        Copia todos los items de la factura y emite la NC inmediatamente.
        """
        max_reintentos = 5
        for intento in range(max_reintentos):
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
                    motivo=motivo or f"Anulacion de factura {factura.numero}",
                )
                break
            except IntegrityError:
                if intento == max_reintentos - 1:
                    raise

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
        Emite nota de credito BORRADOR->EMITIDA.
        Aplica el monto como pago contra la CxC asociada a la factura origen.
        """
        nota = (
            NotaCreditoVenta.objects.select_for_update().filter(pk=nota_id, empresa=empresa).first()
        )
        if not nota:
            raise ResourceNotFoundError("Nota de credito de venta no encontrada.")
        if nota.estado != EstadoNotaCreditoVenta.BORRADOR:
            raise ConflictError(
                f"Solo se puede emitir una nota de credito en BORRADOR (estado: {nota.get_estado_display()})."
            )
        if Decimal(nota.total or 0) <= 0:
            raise BusinessRuleError("No se puede emitir una nota de credito con total cero.")

        items = NotaCreditoVentaItem.all_objects.filter(nota_credito=nota).select_related("producto")
        if not items.exists():
            raise BusinessRuleError("No se puede emitir una nota de credito sin lineas.")

        cls._registrar_reingreso_inventario_si_corresponde(
            nota=nota,
            items=items,
            empresa=empresa,
            usuario=usuario,
        )

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
                    {"cuenta_clave": "VENTAS", "debe": str(nota.subtotal), "haber": "0"},
                    {"cuenta_clave": "IVA_DEBITO", "debe": str(nota.impuestos), "haber": "0"},
                    {"cuenta_clave": "CLIENTES", "debe": "0", "haber": str(nota.total)},
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
        """Anula nota de credito EMITIDA->ANULADA y revierte su impacto financiero."""
        nota = (
            NotaCreditoVenta.objects.select_for_update().filter(pk=nota_id, empresa=empresa).first()
        )
        if not nota:
            raise ResourceNotFoundError("Nota de credito de venta no encontrada.")
        if nota.estado != EstadoNotaCreditoVenta.EMITIDA:
            raise ConflictError(
                f"Solo se puede anular una nota de credito EMITIDA (estado: {nota.get_estado_display()})."
            )

        cls._revertir_reingreso_inventario_si_corresponde(
            nota=nota,
            empresa=empresa,
            usuario=usuario,
        )

        referencia_cxc = f"FV-{nota.factura_origen.numero}-{str(nota.factura_origen_id)[:8]}"
        cxc = CuentaPorCobrar.all_objects.filter(
            empresa=empresa,
            referencia=referencia_cxc,
        ).first()
        if cxc:
            monto_aplicado = Decimal(cxc.monto_total or 0) - Decimal(cxc.saldo or 0)
            monto_revertir = min(Decimal(nota.total or 0), monto_aplicado)
            if monto_revertir > 0:
                CarteraService.revertir_pago_cuenta(
                    cuenta=cxc,
                    monto=monto_revertir,
                    fecha_referencia=nota.fecha_emision,
                )

        estado_anterior = nota.estado
        nota.estado = EstadoNotaCreditoVenta.ANULADA
        nota.anulado_por = usuario
        nota.anulado_en = timezone.now()
        nota.save(update_fields=["estado", "anulado_por", "anulado_en"])
        AccountingBridge.request_entry(
            empresa=empresa,
            aggregate_type="NotaCreditoVenta",
            aggregate_id=nota.id,
            entry_payload={
                "fecha": str(timezone.localdate()),
                "glosa": f"Reversa nota de credito {nota.numero}",
                "referencia_tipo": "NOTA_CREDITO_VENTA_REVERSA",
                "estado_contable_objetivo": EstadoContable.REVERSADO,
                "movimientos": [
                    {"cuenta_clave": "CLIENTES", "debe": str(nota.total), "haber": "0"},
                    {"cuenta_clave": "VENTAS", "debe": "0", "haber": str(nota.subtotal)},
                    {"cuenta_clave": "IVA_DEBITO", "debe": "0", "haber": str(nota.impuestos)},
                ],
            },
            usuario=usuario,
            dedup_key=f"ncv-accounting:{nota.id}:anulada",
        )
        nota.estado_contable = EstadoContable.PENDIENTE
        nota.save(update_fields=["estado_contable", "actualizado_en"])

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
            summary=f"NC {nota.numero}: {estado_anterior} -> {estado_nuevo}",
            changes=cambios,
        )
