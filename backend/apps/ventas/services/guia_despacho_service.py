from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.services import DomainEventService, OutboxService, SecuenciaService
from apps.core.models import TipoDocumento
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import TipoMovimiento
from apps.ventas.models import (
    EstadoGuiaDespacho,
    GuiaDespacho,
    GuiaDespachoItem,
    TipoDocumentoVenta,
    VentaHistorial,
)
from apps.ventas.services.calculo_ventas_service import CalculoVentasService


class GuiaDespachoService:
    """Servicio para la gestión de guías de despacho y su impacto en inventario."""

    @classmethod
    def recalcular_totales(cls, *, guia):
        """Recalcula subtotal, impuestos y total sumando items activos de la guía."""
        items_qs = GuiaDespachoItem.all_objects.filter(guia_despacho=guia)
        CalculoVentasService.recalcular_documento(documento=guia, items_qs=items_qs)

    @classmethod
    def validar_editable(cls, *, guia):
        """Lanza ConflictError si la guía no está en estado BORRADOR."""
        if guia.estado != EstadoGuiaDespacho.BORRADOR:
            raise ConflictError("Solo se puede modificar una guía de despacho en estado BORRADOR.")

    @classmethod
    @transaction.atomic
    def crear_guia(cls, *, datos, empresa, usuario):
        """Crea guía de despacho con folio secuencial, opcionalmente desde pedido de venta."""
        MAX_REINTENTOS = 5
        for intento in range(MAX_REINTENTOS):
            try:
                numero = SecuenciaService.obtener_siguiente_numero(empresa, TipoDocumento.GUIA_DESPACHO)
                guia = GuiaDespacho.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    numero=numero,
                    **datos,
                )
                return guia
            except IntegrityError:
                if intento == MAX_REINTENTOS - 1:
                    raise
        raise BusinessRuleError("No se pudo asignar folio a la guía de despacho.")

    @classmethod
    @transaction.atomic
    def confirmar_guia(cls, *, guia_id, empresa, usuario, bodega_id=None):
        """
        Confirma guía BORRADOR→CONFIRMADA. Registra movimiento SALIDA en inventario
        por cada item con producto que maneja inventario. Actualiza estado del pedido vinculado.
        """
        from apps.inventario.services.inventario_service import InventarioService
        from apps.ventas.services.pedido_venta_service import PedidoVentaService

        guia = (
            GuiaDespacho.objects.select_for_update().filter(pk=guia_id, empresa=empresa).first()
        )
        if not guia:
            raise ResourceNotFoundError("Guía de despacho no encontrada.")
        if guia.estado != EstadoGuiaDespacho.BORRADOR:
            raise ConflictError("Solo se puede confirmar una guía en estado BORRADOR.")

        items = GuiaDespachoItem.all_objects.filter(guia_despacho=guia).select_related("producto")
        if not items.exists():
            raise BusinessRuleError("No se puede confirmar una guía sin líneas.")

        bodega_efectiva = bodega_id or (guia.bodega_id)

        for item in items:
            if item.producto_id and item.producto.maneja_inventario:
                InventarioService.registrar_movimiento(
                    producto_id=item.producto_id,
                    bodega_id=bodega_efectiva,
                    tipo=TipoMovimiento.SALIDA,
                    cantidad=item.cantidad,
                    referencia=f"GD-{guia.numero}",
                    empresa=empresa,
                    usuario=usuario,
                    documento_tipo=TipoDocumentoReferencia.VENTA_FACTURA,
                    documento_id=guia.id,
                )

        estado_anterior = guia.estado
        guia.estado = EstadoGuiaDespacho.CONFIRMADA
        guia.confirmado_por = usuario
        guia.confirmado_en = timezone.now()
        guia.save(update_fields=["estado", "confirmado_por", "confirmado_en"])

        cls.registrar_historial(
            guia=guia,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoGuiaDespacho.CONFIRMADA,
        )

        # Actualizar estado del pedido de venta vinculado si corresponde.
        if guia.pedido_venta_id:
            PedidoVentaService.actualizar_estado_desde_despacho(
                pedido=guia.pedido_venta,
                empresa=empresa,
                usuario=usuario,
            )

        return guia

    @classmethod
    @transaction.atomic
    def anular_guia(cls, *, guia_id, empresa, usuario, bodega_id=None, motivo=""):
        """
        Anula guía CONFIRMADA→ANULADA con movimiento compensatorio ENTRADA en inventario.
        Solo se pueden anular guías ya confirmadas.
        """
        from apps.inventario.services.inventario_service import InventarioService

        guia = (
            GuiaDespacho.objects.select_for_update().filter(pk=guia_id, empresa=empresa).first()
        )
        if not guia:
            raise ResourceNotFoundError("Guía de despacho no encontrada.")
        if guia.estado != EstadoGuiaDespacho.CONFIRMADA:
            raise ConflictError(
                f"Solo se puede anular una guía CONFIRMADA (estado actual: {guia.get_estado_display()})."
            )

        bodega_efectiva = bodega_id or (guia.bodega_id)
        items = GuiaDespachoItem.all_objects.filter(guia_despacho=guia).select_related("producto")

        # Movimiento compensatorio: ENTRADA por cada item que generó un SALIDA.
        for item in items:
            if item.producto_id and item.producto.maneja_inventario:
                InventarioService.registrar_movimiento(
                    producto_id=item.producto_id,
                    bodega_id=bodega_efectiva,
                    tipo=TipoMovimiento.ENTRADA,
                    cantidad=item.cantidad,
                    referencia=f"ANULACION-GD-{guia.numero}",
                    empresa=empresa,
                    usuario=usuario,
                    documento_tipo=TipoDocumentoReferencia.AJUSTE,
                    documento_id=guia.id,
                )

        estado_anterior = guia.estado
        guia.estado = EstadoGuiaDespacho.ANULADA
        guia.anulado_por = usuario
        guia.anulado_en = timezone.now()
        guia.save(update_fields=["estado", "anulado_por", "anulado_en"])

        cls.registrar_historial(
            guia=guia,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoGuiaDespacho.ANULADA,
            motivo=motivo,
        )
        return guia

    @classmethod
    def registrar_historial(cls, *, guia, usuario, estado_anterior, estado_nuevo, motivo="", cambios=None):
        """Registra cambio de estado en historial, DomainEvent y OutboxEvent."""
        from apps.auditoria.services import AuditoriaService

        VentaHistorial.all_objects.create(
            empresa=guia.empresa,
            creado_por=usuario,
            tipo_documento=TipoDocumentoVenta.GUIA,
            documento_id=guia.id,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            motivo=motivo or "",
            cambios=cambios,
        )

        ikey = f"gd-{guia.id}-{estado_nuevo}"

        DomainEventService.record_event(
            empresa=guia.empresa,
            aggregate_type="GuiaDespacho",
            aggregate_id=guia.id,
            event_type=f"guia_despacho.{estado_nuevo.lower()}",
            payload={
                "guia_id": str(guia.id),
                "numero": guia.numero,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "pedido_venta_id": str(guia.pedido_venta_id) if guia.pedido_venta_id else None,
            },
            meta={},
            idempotency_key=ikey,
            usuario=usuario,
        )

        OutboxService.enqueue(
            empresa=guia.empresa,
            topic="ventas.despacho",
            event_name=f"guia_despacho.{estado_nuevo.lower()}",
            payload={
                "guia_id": str(guia.id),
                "numero": guia.numero,
                "cliente_id": str(guia.cliente_id),
                "total": str(guia.total),
            },
            usuario=usuario,
            dedup_key=ikey,
        )

        AuditoriaService.registrar_evento(
            empresa=guia.empresa,
            usuario=usuario,
            module_code="VENTAS",
            action_code=estado_nuevo,
            event_type="guia_despacho.cambio_estado",
            entity_type="GuiaDespacho",
            entity_id=str(guia.id),
            summary=f"Guía {guia.numero}: {estado_anterior} → {estado_nuevo}",
            changes=cambios,
        )
