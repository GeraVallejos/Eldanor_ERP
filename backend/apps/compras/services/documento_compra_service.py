from django.db import transaction
from django.utils import timezone

from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    EstadoOrdenCompra,
    OrdenCompra,
    TipoDocumentoCompra,
)
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import TipoDocumento
from apps.core.services import SecuenciaService
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import MovimientoInventario
from apps.inventario.models import TipoMovimiento
from apps.inventario.services.inventario_service import InventarioService


class DocumentoCompraService:

    @staticmethod
    def avanzar_orden_si_borrador(*, documento):
        """Si el documento tiene OC asociada en BORRADOR, la avanza a ENVIADA."""
        orden = documento.orden_compra
        if orden is None:
            return
        if orden.estado == EstadoOrdenCompra.BORRADOR:
            OrdenCompra.all_objects.filter(id=orden.id).update(estado=EstadoOrdenCompra.ENVIADA)

    @staticmethod
    def validar_documento_editable(*, documento):
        if documento.estado == EstadoDocumentoCompra.CONFIRMADO:
            raise ConflictError("No se puede editar un documento confirmado. Use la accion corregir.")
        if documento.estado == EstadoDocumentoCompra.ANULADO:
            raise ConflictError("No se puede editar un documento anulado.")

    @staticmethod
    @transaction.atomic
    def confirmar_guia(*, documento_id, empresa, usuario, bodega_id=None):
        documento = (
            DocumentoCompraProveedor.all_objects
            .select_for_update()
            .filter(id=documento_id, empresa=empresa, tipo_documento=TipoDocumentoCompra.GUIA_RECEPCION)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Guía de recepción no encontrada.")

        if documento.estado == EstadoDocumentoCompra.ANULADO:
            raise ConflictError("El documento está anulado.")

        if documento.estado == EstadoDocumentoCompra.CONFIRMADO:
            return documento

        items = list(
            DocumentoCompraProveedorItem.all_objects
            .select_related("producto")
            .filter(empresa=empresa, documento=documento)
        )
        if not items:
            raise BusinessRuleError("No se puede confirmar una guía sin items.")

        for item in items:
            if item.cantidad <= 0:
                raise BusinessRuleError("La cantidad de cada item debe ser mayor a cero.")
            if item.precio_unitario < 0:
                raise BusinessRuleError("El precio unitario no puede ser negativo.")

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                bodega_id=bodega_id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=item.cantidad,
                referencia=f"GUIA {documento.folio}",
                empresa=empresa,
                usuario=usuario,
                costo_unitario=item.precio_unitario,
                documento_tipo=TipoDocumentoReferencia.GUIA_RECEPCION,
                documento_id=documento.id,
            )

        documento.estado = EstadoDocumentoCompra.CONFIRMADO
        documento.save(update_fields=["estado"])
        return documento

    @staticmethod
    @transaction.atomic
    def confirmar_factura(*, documento_id, empresa, usuario, bodega_id=None):
        documento = (
            DocumentoCompraProveedor.all_objects
            .select_for_update()
            .filter(id=documento_id, empresa=empresa, tipo_documento=TipoDocumentoCompra.FACTURA_COMPRA)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Factura de compra no encontrada.")

        if documento.estado == EstadoDocumentoCompra.ANULADO:
            raise ConflictError("El documento está anulado.")

        if documento.estado == EstadoDocumentoCompra.CONFIRMADO:
            return documento

        items = list(
            DocumentoCompraProveedorItem.all_objects
            .select_related("producto")
            .filter(empresa=empresa, documento=documento)
        )
        if not items:
            raise BusinessRuleError("No se puede confirmar una factura sin items.")

        for item in items:
            if item.cantidad <= 0:
                raise BusinessRuleError("La cantidad de cada item debe ser mayor a cero.")
            if item.precio_unitario < 0:
                raise BusinessRuleError("El precio unitario no puede ser negativo.")

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                bodega_id=bodega_id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=item.cantidad,
                referencia=f"FACTURA {documento.folio}",
                empresa=empresa,
                usuario=usuario,
                costo_unitario=item.precio_unitario,
                documento_tipo=TipoDocumentoReferencia.FACTURA_COMPRA,
                documento_id=documento.id,
            )

        documento.estado = EstadoDocumentoCompra.CONFIRMADO
        documento.save(update_fields=["estado"])
        return documento

    @staticmethod
    @transaction.atomic
    def anular_documento(*, documento_id, empresa, usuario, bodega_id=None):
        documento = (
            DocumentoCompraProveedor.all_objects
            .select_for_update()
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Documento de compra no encontrado.")

        if documento.estado == EstadoDocumentoCompra.ANULADO:
            return documento

        # Documentos confirmados generan movimiento compensatorio al anularse
        if (
            documento.estado == EstadoDocumentoCompra.CONFIRMADO
            and documento.tipo_documento in {TipoDocumentoCompra.GUIA_RECEPCION, TipoDocumentoCompra.FACTURA_COMPRA}
        ):
            items = list(
                DocumentoCompraProveedorItem.all_objects
                .select_related("producto")
                .filter(empresa=empresa, documento=documento)
            )
            doc_tipo_referencia = (
                TipoDocumentoReferencia.GUIA_RECEPCION
                if documento.tipo_documento == TipoDocumentoCompra.GUIA_RECEPCION
                else TipoDocumentoReferencia.FACTURA_COMPRA
            )
            prefijo = "GUIA" if documento.tipo_documento == TipoDocumentoCompra.GUIA_RECEPCION else "FACTURA"
            tiene_movimientos_previos = MovimientoInventario.all_objects.filter(
                empresa=empresa,
                documento_tipo=doc_tipo_referencia,
                documento_id=documento.id,
            ).exists()
            if tiene_movimientos_previos:
                for item in items:
                    InventarioService.registrar_movimiento(
                        producto_id=item.producto_id,
                        bodega_id=bodega_id,
                        tipo=TipoMovimiento.SALIDA,
                        cantidad=item.cantidad,
                        costo_unitario=item.precio_unitario,
                        referencia=f"ANULACION {prefijo} {documento.folio}",
                        empresa=empresa,
                        usuario=usuario,
                        documento_tipo=doc_tipo_referencia,
                        documento_id=documento.id,
                    )

        documento.estado = EstadoDocumentoCompra.ANULADO
        documento.save(update_fields=["estado"])
        return documento

    @staticmethod
    @transaction.atomic
    def corregir_documento(*, documento_id, empresa, usuario, motivo, bodega_id=None):
        documento = (
            DocumentoCompraProveedor.all_objects
            .select_for_update()
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Documento de compra no encontrado.")

        motivo_normalizado = (motivo or "").strip()
        if not motivo_normalizado:
            raise BusinessRuleError("Debe indicar un motivo de correccion.")

        if documento.estado != EstadoDocumentoCompra.CONFIRMADO:
            raise ConflictError("Solo se puede corregir un documento confirmado.")

        DocumentoCompraService.anular_documento(
            documento_id=documento.id,
            empresa=empresa,
            usuario=usuario,
            bodega_id=bodega_id,
        )

        clon = DocumentoCompraProveedor.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            tipo_documento=documento.tipo_documento,
            proveedor=documento.proveedor,
            folio=documento.folio,
            serie=documento.serie,
            fecha_emision=documento.fecha_emision,
            fecha_recepcion=documento.fecha_recepcion,
            subtotal_neto=documento.subtotal_neto,
            impuestos=documento.impuestos,
            total=documento.total,
            estado=EstadoDocumentoCompra.BORRADOR,
            observaciones=documento.observaciones,
            orden_compra=documento.orden_compra,
            recepcion_compra=documento.recepcion_compra,
            documento_origen=documento,
            motivo_correccion=motivo_normalizado,
            corregido_por=usuario,
            corregido_en=timezone.now(),
            uuid_externo=None,
        )

        items_originales = list(
            DocumentoCompraProveedorItem.all_objects.filter(empresa=empresa, documento=documento)
        )
        for item in items_originales:
            DocumentoCompraProveedorItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                documento=clon,
                producto=item.producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                descuento=item.descuento,
                subtotal=item.subtotal,
                recepcion_item=item.recepcion_item,
            )

        return clon

    @staticmethod
    @transaction.atomic
    def duplicar_documento(*, documento_id, empresa, usuario):
        """Duplica un documento sin anular el original. Crea un nuevo borrador."""
        documento = (
            DocumentoCompraProveedor.all_objects
            .filter(id=documento_id, empresa=empresa)
            .first()
        )
        if not documento:
            raise ResourceNotFoundError("Documento de compra no encontrado.")

        # Obtener siguiente número de secuencia
        folio_siguiente = SecuenciaService.obtener_siguiente_numero(
            empresa=empresa,
            tipo_documento=TipoDocumento.DOCUMENTO_COMPRA
        )

        # Crear clon en estado BORRADOR
        clon = DocumentoCompraProveedor.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            tipo_documento=documento.tipo_documento,
            proveedor=documento.proveedor,
            folio=folio_siguiente,
            serie=documento.serie,
            fecha_emision=documento.fecha_emision,
            fecha_recepcion=documento.fecha_recepcion,
            subtotal_neto=documento.subtotal_neto,
            impuestos=documento.impuestos,
            total=documento.total,
            estado=EstadoDocumentoCompra.BORRADOR,
            observaciones=documento.observaciones,
            orden_compra=documento.orden_compra,
            recepcion_compra=documento.recepcion_compra,
            documento_origen=documento,  # Registrar el origen para auditoría
            uuid_externo=None,
        )

        # Copiar items
        items_originales = list(
            DocumentoCompraProveedorItem.all_objects.filter(empresa=empresa, documento=documento)
        )
        for item in items_originales:
            DocumentoCompraProveedorItem.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                documento=clon,
                producto=item.producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                descuento=item.descuento,
                subtotal=item.subtotal,
                recepcion_item=item.recepcion_item,
            )

        return clon
