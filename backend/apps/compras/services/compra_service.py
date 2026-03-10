from django.db import transaction
from django.db.models import Sum

from apps.compras.models import (
    EstadoOrdenCompra,
    EstadoRecepcion,
    OrdenCompra,
    OrdenCompraItem,
    RecepcionCompra,
    RecepcionCompraItem,
)
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import TipoMovimiento
from apps.inventario.services.inventario_service import InventarioService


class OrdenCompraService:
    @staticmethod
    @transaction.atomic
    def enviar_orden(*, orden_id, empresa):
        orden = OrdenCompra.all_objects.select_for_update().filter(id=orden_id, empresa=empresa).first()
        if not orden:
            raise ResourceNotFoundError("Orden de compra no encontrada.")

        if orden.estado != EstadoOrdenCompra.BORRADOR:
            raise ConflictError("Solo se puede enviar una orden en estado borrador.")

        if not OrdenCompraItem.all_objects.filter(empresa=empresa, orden_compra=orden).exists():
            raise BusinessRuleError("No se puede enviar una orden de compra sin items.")

        orden.estado = EstadoOrdenCompra.ENVIADA
        orden.save(update_fields=["estado"])
        return orden

    @staticmethod
    @transaction.atomic
    def anular_orden(*, orden_id, empresa):
        orden = OrdenCompra.all_objects.select_for_update().filter(id=orden_id, empresa=empresa).first()
        if not orden:
            raise ResourceNotFoundError("Orden de compra no encontrada.")

        if orden.estado in {EstadoOrdenCompra.PARCIAL, EstadoOrdenCompra.RECIBIDA}:
            raise ConflictError("No se puede anular una orden con recepciones confirmadas.")

        if orden.estado == EstadoOrdenCompra.CANCELADA:
            return orden

        orden.estado = EstadoOrdenCompra.CANCELADA
        orden.save(update_fields=["estado"])
        return orden


class RecepcionCompraService:
    @staticmethod
    def _cantidad_recibida_confirmada(*, empresa, orden_item, excluir_recepcion_id=None):
        queryset = RecepcionCompraItem.all_objects.filter(
            empresa=empresa,
            orden_item=orden_item,
            recepcion__estado=EstadoRecepcion.CONFIRMADA,
        )
        if excluir_recepcion_id:
            queryset = queryset.exclude(recepcion_id=excluir_recepcion_id)
        return queryset.aggregate(total=Sum("cantidad"))["total"] or 0

    @staticmethod
    @transaction.atomic
    def confirmar_recepcion(*, recepcion_id, empresa, usuario, bodega_id=None):
        recepcion = (
            RecepcionCompra.all_objects
            .select_for_update()
            .select_related("orden_compra")
            .filter(id=recepcion_id, empresa=empresa)
            .first()
        )
        if not recepcion:
            raise ResourceNotFoundError("Recepcion de compra no encontrada.")

        if recepcion.estado == EstadoRecepcion.CONFIRMADA:
            return recepcion

        orden = recepcion.orden_compra
        if orden.estado in {EstadoOrdenCompra.CANCELADA, EstadoOrdenCompra.RECIBIDA}:
            raise ConflictError("La orden asociada no admite nuevas recepciones.")

        items = list(
            RecepcionCompraItem.all_objects
            .select_related("orden_item", "producto")
            .filter(empresa=empresa, recepcion=recepcion)
        )
        if not items:
            raise BusinessRuleError("No se puede confirmar una recepcion sin items.")

        for item in items:
            if item.orden_item.orden_compra_id != orden.id:
                raise BusinessRuleError("El item de recepcion no pertenece a la orden de compra.")

            recibido_previo = RecepcionCompraService._cantidad_recibida_confirmada(
                empresa=empresa,
                orden_item=item.orden_item,
                excluir_recepcion_id=recepcion.id,
            )
            pendiente = item.orden_item.cantidad - recibido_previo
            if item.cantidad <= 0:
                raise BusinessRuleError("La cantidad recepcionada debe ser mayor a cero.")
            if item.cantidad > pendiente:
                raise ConflictError("La cantidad recepcionada supera lo pendiente de la orden.")

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                bodega_id=bodega_id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=item.cantidad,
                referencia=f"RECEPCION-{recepcion.id}",
                empresa=empresa,
                usuario=usuario,
                costo_unitario=item.orden_item.precio_unitario,
                documento_tipo=TipoDocumentoReferencia.COMPRA_RECEPCION,
                documento_id=recepcion.id,
            )

        recepcion.estado = EstadoRecepcion.CONFIRMADA
        recepcion.save(update_fields=["estado"])

        orden_items = list(OrdenCompraItem.all_objects.filter(empresa=empresa, orden_compra=orden))
        if orden_items:
            completos = 0
            con_algo = 0
            for orden_item in orden_items:
                total_recibido = RecepcionCompraService._cantidad_recibida_confirmada(
                    empresa=empresa,
                    orden_item=orden_item,
                )
                if total_recibido > 0:
                    con_algo += 1
                if total_recibido >= orden_item.cantidad:
                    completos += 1

            if completos == len(orden_items):
                orden.estado = EstadoOrdenCompra.RECIBIDA
            elif con_algo > 0:
                orden.estado = EstadoOrdenCompra.PARCIAL
            elif orden.estado == EstadoOrdenCompra.BORRADOR:
                orden.estado = EstadoOrdenCompra.ENVIADA
            orden.save(update_fields=["estado"])

        return recepcion
