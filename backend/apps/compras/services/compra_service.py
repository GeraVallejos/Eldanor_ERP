from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.compras.models import (
    DocumentoCompraProveedor,
    EstadoDocumentoCompra,
    EstadoOrdenCompra,
    EstadoRecepcion,
    OrdenCompra,
    OrdenCompraItem,
    RecepcionCompra,
    RecepcionCompraItem,
)
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import TipoDocumento
from apps.core.services import SecuenciaService
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import TipoMovimiento
from apps.inventario.services.inventario_service import InventarioService


class OrdenCompraService:
    @staticmethod
    def validar_orden_editable(*, orden):
        if orden.estado != EstadoOrdenCompra.BORRADOR:
            raise ConflictError(
                "Solo se puede editar una orden en estado borrador. "
                "Use la accion corregir para ordenes ya enviadas."
            )

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

        if DocumentoCompraProveedor.all_objects.filter(
            empresa=empresa,
            orden_compra=orden,
        ).exclude(estado=EstadoDocumentoCompra.ANULADO).exists():
            raise ConflictError("No se puede anular una orden con documentos de compra activos asociados.")

        if orden.estado in {EstadoOrdenCompra.PARCIAL, EstadoOrdenCompra.RECIBIDA}:
            raise ConflictError("No se puede anular una orden con recepciones confirmadas.")

        if orden.estado == EstadoOrdenCompra.CANCELADA:
            return orden

        orden.estado = EstadoOrdenCompra.CANCELADA
        orden.save(update_fields=["estado"])
        return orden

    @staticmethod
    @transaction.atomic
    def eliminar_orden_sin_documentos(*, orden_id, empresa):
        orden = OrdenCompra.all_objects.select_for_update().filter(id=orden_id, empresa=empresa).first()
        if not orden:
            raise ResourceNotFoundError("Orden de compra no encontrada.")

        # Verificar que no tenga documentos asociados
        if orden.documentos_compra.exists():
            raise ConflictError("No se puede eliminar una orden que tiene documentos asociados.")

        orden.delete()
        return None

    @staticmethod
    @transaction.atomic
    def corregir_orden(*, orden_id, empresa, usuario, motivo):
        """Anula la orden y crea un nuevo borrador con los mismos datos."""
        orden = OrdenCompra.all_objects.select_for_update().filter(id=orden_id, empresa=empresa).first()
        if not orden:
            raise ResourceNotFoundError("Orden de compra no encontrada.")

        if DocumentoCompraProveedor.all_objects.filter(
            empresa=empresa,
            orden_compra=orden,
        ).exclude(estado=EstadoDocumentoCompra.ANULADO).exists():
            raise ConflictError("No se puede corregir una orden con documentos de compra activos asociados.")

        motivo_normalizado = (motivo or "").strip()
        if not motivo_normalizado:
            raise BusinessRuleError("Debe indicar un motivo de correccion.")

        if orden.estado not in {EstadoOrdenCompra.ENVIADA, EstadoOrdenCompra.PARCIAL, EstadoOrdenCompra.RECIBIDA}:
            raise ConflictError("Solo se pueden corregir ordenes enviadas o recibidas.")

        # Anular la orden original
        orden.estado = EstadoOrdenCompra.CANCELADA
        orden.save(update_fields=["estado"])

        # Obtener siguiente número de secuencia
        numero_siguiente = SecuenciaService.obtener_siguiente_numero(
            empresa=empresa,
            tipo_documento=TipoDocumento.ORDEN_COMPRA
        )

        # Crear nueva orden en borrador
        nueva_orden = OrdenCompra.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            proveedor=orden.proveedor,
            numero=numero_siguiente,
            fecha_emision=orden.fecha_emision,
            fecha_entrega=orden.fecha_entrega,
            estado=EstadoOrdenCompra.BORRADOR,
            observaciones=orden.observaciones,
            subtotal=orden.subtotal,
            impuestos=orden.impuestos,
            total=orden.total,
        )

        # Copiar items
        items_originales = list(
            OrdenCompraItem.all_objects.filter(empresa=empresa, orden_compra=orden)
        )
        for item in items_originales:
            OrdenCompraItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                orden_compra=nueva_orden,
                producto=item.producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                impuesto=item.impuesto,
            )

        return nueva_orden

    @staticmethod
    @transaction.atomic
    def duplicar_orden(*, orden_id, empresa, usuario):
        """Duplica una orden sin anular la original. Crea un nuevo borrador."""
        orden = OrdenCompra.all_objects.filter(id=orden_id, empresa=empresa).first()
        if not orden:
            raise ResourceNotFoundError("Orden de compra no encontrada.")

        # Obtener siguiente número de secuencia
        numero_siguiente = SecuenciaService.obtener_siguiente_numero(
            empresa=empresa,
            tipo_documento=TipoDocumento.ORDEN_COMPRA
        )

        # Crear nueva orden en borrador
        nueva_orden = OrdenCompra.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            proveedor=orden.proveedor,
            numero=numero_siguiente,
            fecha_emision=orden.fecha_emision,
            fecha_entrega=orden.fecha_entrega,
            estado=EstadoOrdenCompra.BORRADOR,
            observaciones=orden.observaciones,
            subtotal=orden.subtotal,
            impuestos=orden.impuestos,
            total=orden.total,
        )

        # Copiar items
        items_originales = list(
            OrdenCompraItem.all_objects.filter(empresa=empresa, orden_compra=orden)
        )
        for item in items_originales:
            OrdenCompraItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                orden_compra=nueva_orden,
                producto=item.producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                impuesto=item.impuesto,
            )

        return nueva_orden


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
        if orden and orden.estado in {EstadoOrdenCompra.CANCELADA, EstadoOrdenCompra.RECIBIDA}:
            raise ConflictError("La orden asociada no admite nuevas recepciones.")

        items = list(
            RecepcionCompraItem.all_objects
            .select_related("orden_item", "producto")
            .filter(empresa=empresa, recepcion=recepcion)
        )
        if not items:
            raise BusinessRuleError("No se puede confirmar una recepcion sin items.")

        for item in items:
            if item.cantidad <= 0:
                raise BusinessRuleError("La cantidad recepcionada debe ser mayor a cero.")

            costo_unitario = item.precio_unitario
            if orden:
                if not item.orden_item_id:
                    raise BusinessRuleError("Los items de una recepcion con OC deben tener item de OC asociado.")

                if item.orden_item.orden_compra_id != orden.id:
                    raise BusinessRuleError("El item de recepcion no pertenece a la orden de compra.")

                recibido_previo = RecepcionCompraService._cantidad_recibida_confirmada(
                    empresa=empresa,
                    orden_item=item.orden_item,
                    excluir_recepcion_id=recepcion.id,
                )
                pendiente = item.orden_item.cantidad - recibido_previo
                if item.cantidad > pendiente:
                    raise ConflictError("La cantidad recepcionada supera lo pendiente de la orden.")

                costo_unitario = item.orden_item.precio_unitario
            elif costo_unitario < 0:
                raise BusinessRuleError("El precio unitario no puede ser negativo en recepciones sin OC.")

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                bodega_id=bodega_id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=item.cantidad,
                referencia=f"RECEPCION-{recepcion.id}",
                empresa=empresa,
                usuario=usuario,
                costo_unitario=costo_unitario,
                documento_tipo=TipoDocumentoReferencia.COMPRA_RECEPCION,
                documento_id=recepcion.id,
            )

        recepcion.estado = EstadoRecepcion.CONFIRMADA
        recepcion.save(update_fields=["estado"])

        orden_items = list(OrdenCompraItem.all_objects.filter(empresa=empresa, orden_compra=orden)) if orden else []
        if orden and orden_items:
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
