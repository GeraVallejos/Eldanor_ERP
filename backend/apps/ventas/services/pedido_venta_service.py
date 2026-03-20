from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum

from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.services import DomainEventService, OutboxService, SecuenciaService
from apps.core.models import TipoDocumento
from apps.documentos.models import TipoDocumentoReferencia
from apps.ventas.models import (
    EstadoPedidoVenta,
    PedidoVenta,
    PedidoVentaItem,
    TipoDocumentoVenta,
    VentaHistorial,
)
from apps.ventas.services.calculo_ventas_service import CalculoVentasService


class PedidoVentaService:
    """Servicio central para la gestión de pedidos de venta."""

    ESTADOS_ANULABLES = {
        EstadoPedidoVenta.BORRADOR,
        EstadoPedidoVenta.CONFIRMADO,
        EstadoPedidoVenta.EN_PROCESO,
    }

    @classmethod
    def recalcular_totales(cls, *, pedido):
        """Recalcula subtotal, impuestos y total sumando los items activos del pedido."""
        items_qs = PedidoVentaItem.all_objects.filter(pedido_venta=pedido)
        CalculoVentasService.recalcular_documento(documento=pedido, items_qs=items_qs)

    @classmethod
    def validar_editable(cls, *, pedido):
        """Lanza ConflictError si el pedido no está en estado BORRADOR."""
        if pedido.estado != EstadoPedidoVenta.BORRADOR:
            raise ConflictError("Solo se puede modificar un pedido en estado BORRADOR.")

    @classmethod
    @transaction.atomic
    def crear_pedido(cls, *, datos, empresa, usuario):
        """Crea un nuevo pedido de venta con número de folio secuencial."""
        MAX_REINTENTOS = 5
        for intento in range(MAX_REINTENTOS):
            try:
                numero = SecuenciaService.obtener_siguiente_numero(empresa, TipoDocumento.PEDIDO_VENTA)
                pedido = PedidoVenta.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    numero=numero,
                    **datos,
                )
                return pedido
            except IntegrityError:
                if intento == MAX_REINTENTOS - 1:
                    raise
        # Inalcanzable, pero satisface el type-checker.
        raise BusinessRuleError("No se pudo asignar folio al pedido de venta.")

    @classmethod
    @transaction.atomic
    def confirmar_pedido(cls, *, pedido_id, empresa, usuario):
        """Confirma pedido BORRADOR→CONFIRMADO. Reserva stock para items con inventario."""
        from apps.inventario.services.inventario_service import InventarioService

        pedido = (
            PedidoVenta.objects.select_for_update().filter(pk=pedido_id, empresa=empresa).first()
        )
        if not pedido:
            raise ResourceNotFoundError("Pedido de venta no encontrado.")
        if pedido.estado != EstadoPedidoVenta.BORRADOR:
            raise ConflictError("Solo se puede confirmar un pedido en estado BORRADOR.")

        items = PedidoVentaItem.all_objects.filter(pedido_venta=pedido).select_related("producto")
        if not items.exists():
            raise BusinessRuleError("No se puede confirmar un pedido sin líneas.")

        estado_anterior = pedido.estado

        # Reservar stock para cada item que maneja inventario.
        for item in items:
            if item.producto_id and item.producto.maneja_inventario:
                InventarioService.reservar_stock(
                    producto_id=item.producto_id,
                    bodega_id=None,
                    cantidad=item.cantidad,
                    documento_tipo=TipoDocumentoReferencia.PEDIDO_VENTA,
                    documento_id=pedido.id,
                    empresa=empresa,
                    usuario=usuario,
                )

        pedido.estado = EstadoPedidoVenta.CONFIRMADO
        pedido.save(update_fields=["estado"])

        cls.registrar_historial(
            pedido=pedido,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoPedidoVenta.CONFIRMADO,
        )
        return pedido

    @classmethod
    @transaction.atomic
    def anular_pedido(cls, *, pedido_id, empresa, usuario, motivo=""):
        """Anula pedido y libera reservas de stock activas. Solo estados pre-despacho."""
        from apps.inventario.services.inventario_service import InventarioService

        pedido = (
            PedidoVenta.objects.select_for_update().filter(pk=pedido_id, empresa=empresa).first()
        )
        if not pedido:
            raise ResourceNotFoundError("Pedido de venta no encontrado.")
        if pedido.estado not in cls.ESTADOS_ANULABLES:
            raise ConflictError(
                f"No se puede anular un pedido en estado {pedido.get_estado_display()}."
            )

        estados_con_reserva = {EstadoPedidoVenta.CONFIRMADO, EstadoPedidoVenta.EN_PROCESO}

        # Liberar reservas de stock si el pedido ya estaba confirmado.
        if pedido.estado in estados_con_reserva:
            items = PedidoVentaItem.all_objects.filter(pedido_venta=pedido).select_related("producto")
            for item in items:
                if item.producto_id and item.producto.maneja_inventario:
                    InventarioService.liberar_reserva(
                        producto_id=item.producto_id,
                        bodega_id=None,
                        documento_tipo=TipoDocumentoReferencia.PEDIDO_VENTA,
                        documento_id=pedido.id,
                        empresa=empresa,
                    )

        estado_anterior = pedido.estado
        pedido.estado = EstadoPedidoVenta.ANULADO
        pedido.save(update_fields=["estado"])

        cls.registrar_historial(
            pedido=pedido,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=EstadoPedidoVenta.ANULADO,
            motivo=motivo,
        )
        return pedido

    @classmethod
    @transaction.atomic
    def eliminar_pedido(cls, *, pedido_id, empresa, usuario):
        """Elimina físicamente un pedido solo si está en estado BORRADOR."""
        pedido = PedidoVenta.objects.filter(pk=pedido_id, empresa=empresa).first()
        if not pedido:
            raise ResourceNotFoundError("Pedido de venta no encontrado.")
        if pedido.estado != EstadoPedidoVenta.BORRADOR:
            raise ConflictError("Solo se pueden eliminar pedidos en estado BORRADOR.")
        pedido.delete()

    @classmethod
    @transaction.atomic
    def duplicar_pedido(cls, *, pedido_id, empresa, usuario):
        """Clona un pedido existente con nuevo folio en estado BORRADOR."""
        original = PedidoVenta.objects.filter(pk=pedido_id, empresa=empresa).first()
        if not original:
            raise ResourceNotFoundError("Pedido de venta no encontrado.")

        MAX_REINTENTOS = 5
        for intento in range(MAX_REINTENTOS):
            try:
                nuevo_numero = SecuenciaService.obtener_siguiente_numero(
                    empresa, TipoDocumento.PEDIDO_VENTA
                )
                nuevo = PedidoVenta.all_objects.create(
                    empresa=empresa,
                    creado_por=usuario,
                    numero=nuevo_numero,
                    cliente_id=original.cliente_id,
                    fecha_emision=original.fecha_emision,
                    fecha_entrega=original.fecha_entrega,
                    descuento=original.descuento,
                    lista_precio_id=original.lista_precio_id,
                    observaciones=original.observaciones,
                    estado=EstadoPedidoVenta.BORRADOR,
                )
                break
            except IntegrityError:
                if intento == MAX_REINTENTOS - 1:
                    raise

        for item in PedidoVentaItem.all_objects.filter(pedido_venta=original):
            PedidoVentaItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                pedido_venta=nuevo,
                producto_id=item.producto_id,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                descuento=item.descuento,
                impuesto_id=item.impuesto_id,
                impuesto_porcentaje=item.impuesto_porcentaje,
            )

        cls.recalcular_totales(pedido=nuevo)
        return nuevo

    @classmethod
    def actualizar_estado_desde_despacho(cls, *, pedido, empresa, usuario):
        """
        Recalcula estado del pedido según proporción despachada.
        Llamado por GuiaDespachoService tras confirmar una guía vinculada.
        """
        if pedido.estado not in {EstadoPedidoVenta.CONFIRMADO, EstadoPedidoVenta.EN_PROCESO}:
            return

        from apps.ventas.models import GuiaDespachoItem

        items_pedido = PedidoVentaItem.all_objects.filter(pedido_venta=pedido)
        totalmente_despachado = True

        for item_pv in items_pedido:
            despachado = (
                GuiaDespachoItem.all_objects.filter(
                    pedido_item=item_pv,
                    guia_despacho__estado="CONFIRMADA",
                )
                .aggregate(total=Sum("cantidad", default=Decimal("0")))["total"]
                or Decimal("0")
            )
            if despachado < item_pv.cantidad:
                totalmente_despachado = False
                break

        estado_anterior = pedido.estado
        nuevo_estado = (
            EstadoPedidoVenta.DESPACHADO if totalmente_despachado else EstadoPedidoVenta.EN_PROCESO
        )

        if pedido.estado != nuevo_estado:
            pedido.estado = nuevo_estado
            pedido.save(update_fields=["estado"])
            cls.registrar_historial(
                pedido=pedido,
                usuario=usuario,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
            )

    @classmethod
    def registrar_historial(cls, *, pedido, usuario, estado_anterior, estado_nuevo, motivo="", cambios=None):
        """Registra cambio de estado en historial, DomainEvent, OutboxEvent y Auditoria."""
        from apps.auditoria.services import AuditoriaService

        VentaHistorial.all_objects.create(
            empresa=pedido.empresa,
            creado_por=usuario,
            tipo_documento=TipoDocumentoVenta.PEDIDO,
            documento_id=pedido.id,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            motivo=motivo or "",
            cambios=cambios,
        )

        ikey = f"pv-{pedido.id}-{estado_nuevo}"

        DomainEventService.record_event(
            empresa=pedido.empresa,
            aggregate_type="PedidoVenta",
            aggregate_id=pedido.id,
            event_type=f"pedido_venta.{estado_nuevo.lower()}",
            payload={
                "pedido_id": str(pedido.id),
                "numero": pedido.numero,
                "estado_anterior": estado_anterior,
                "estado_nuevo": estado_nuevo,
                "motivo": motivo,
            },
            meta={},
            idempotency_key=ikey,
            usuario=usuario,
        )

        OutboxService.enqueue(
            empresa=pedido.empresa,
            topic="ventas.pedido",
            event_name=f"pedido_venta.{estado_nuevo.lower()}",
            payload={
                "pedido_id": str(pedido.id),
                "numero": pedido.numero,
                "cliente_id": str(pedido.cliente_id),
                "total": str(pedido.total),
            },
            usuario=usuario,
            dedup_key=ikey,
        )

        AuditoriaService.registrar_evento(
            empresa=pedido.empresa,
            usuario=usuario,
            module_code="VENTAS",
            action_code=estado_nuevo,
            event_type="pedido_venta.cambio_estado",
            entity_type="PedidoVenta",
            entity_id=str(pedido.id),
            summary=f"Pedido {pedido.numero}: {estado_anterior} → {estado_nuevo}",
            changes=cambios,
        )
