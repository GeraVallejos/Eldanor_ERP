from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    EstadoOrdenCompra,
    OrdenCompra,
    OrdenCompraItem,
    EstadoRecepcion,
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
    def _pct_config(value):
        try:
            return Decimal(str(value or 0))
        except Exception:
            return Decimal("0")

    @staticmethod
    def recalcular_totales(*, documento):
        items = list(
            DocumentoCompraProveedorItem.all_objects.select_related("producto__impuesto").filter(
                empresa=documento.empresa,
                documento=documento,
            )
        )

        subtotal_neto = Decimal("0.00")
        impuestos = Decimal("0.00")

        for item in items:
            subtotal = Decimal(item.subtotal or 0)
            subtotal_neto += subtotal

            tasa = Decimal("0")
            producto = getattr(item, "producto", None)
            if producto and getattr(producto, "impuesto", None) and producto.impuesto.porcentaje is not None:
                tasa = Decimal(producto.impuesto.porcentaje)

            impuestos += (subtotal * tasa / Decimal("100")).quantize(Decimal("0.01"))

        subtotal_neto = subtotal_neto.quantize(Decimal("0.01"))
        impuestos = impuestos.quantize(Decimal("0.01"))
        total = (subtotal_neto + impuestos).quantize(Decimal("0.01"))

        DocumentoCompraProveedor.all_objects.filter(id=documento.id).update(
            subtotal_neto=subtotal_neto,
            impuestos=impuestos,
            total=total,
        )

    @staticmethod
    def _validar_three_way_match(*, documento, items):
        orden = documento.orden_compra
        if not orden:
            return

        qty_tolerance_pct = DocumentoCompraService._pct_config(
            getattr(settings, "ERP_OC_QTY_TOLERANCE_PCT", 0)
        )
        price_tolerance_pct = DocumentoCompraService._pct_config(
            getattr(settings, "ERP_OC_PRICE_TOLERANCE_PCT", 0)
        )
        qty_factor = Decimal("1") + (qty_tolerance_pct / Decimal("100"))

        oc_items = list(
            OrdenCompraItem.all_objects.filter(empresa=documento.empresa, orden_compra=orden)
        )
        if not oc_items:
            raise BusinessRuleError("La OC asociada no tiene items para validar el documento.")

        oc_by_producto = {}
        for oc_item in oc_items:
            key = str(oc_item.producto_id)
            if key not in oc_by_producto:
                oc_by_producto[key] = {
                    "cantidad": Decimal("0"),
                    "precio": Decimal(oc_item.precio_unitario or 0),
                }
            oc_by_producto[key]["cantidad"] += Decimal(oc_item.cantidad or 0)

        current_qty_by_producto = {}
        for item in items:
            key = str(item.producto_id)
            if key not in oc_by_producto:
                raise BusinessRuleError("El documento incluye productos que no estan en la OC asociada.")

            current_qty_by_producto[key] = current_qty_by_producto.get(key, Decimal("0")) + Decimal(item.cantidad or 0)

            oc_price = oc_by_producto[key]["precio"]
            doc_price = Decimal(item.precio_unitario or 0)
            if oc_price > 0:
                delta_pct = (abs(doc_price - oc_price) / oc_price) * Decimal("100")
                if delta_pct > price_tolerance_pct:
                    raise ConflictError(
                        "El precio del documento excede la tolerancia permitida respecto a la OC."
                    )
            elif doc_price != oc_price:
                raise ConflictError("El precio del documento no coincide con la OC asociada.")

        consumido_confirmado = (
            DocumentoCompraProveedorItem.all_objects
            .filter(
                empresa=documento.empresa,
                documento__orden_compra=orden,
                documento__estado=EstadoDocumentoCompra.CONFIRMADO,
            )
            .exclude(documento_id=documento.id)
            .values("producto_id")
            .annotate(cantidad=Sum("cantidad"))
        )
        consumido_by_producto = {
            str(row["producto_id"]): Decimal(row["cantidad"] or 0) for row in consumido_confirmado
        }

        for producto_id, qty_actual in current_qty_by_producto.items():
            qty_orden = Decimal(oc_by_producto[producto_id]["cantidad"] or 0)
            qty_consumida = Decimal(consumido_by_producto.get(producto_id, 0))
            qty_max = (qty_orden * qty_factor).quantize(Decimal("0.01"))
            if (qty_consumida + qty_actual) > qty_max:
                raise ConflictError(
                    "La cantidad del documento supera lo permitido por la OC considerando tolerancias."
                )

        recepcion = documento.recepcion_compra
        if recepcion:
            if recepcion.estado != EstadoRecepcion.CONFIRMADA:
                raise ConflictError("No se puede confirmar documento con recepcion no confirmada.")

            recepcion_items = list(recepcion.items.all())
            rec_by_producto = {}
            for rec_item in recepcion_items:
                key = str(rec_item.producto_id)
                rec_by_producto[key] = rec_by_producto.get(key, Decimal("0")) + Decimal(rec_item.cantidad or 0)

            for producto_id, qty_actual in current_qty_by_producto.items():
                qty_rec = Decimal(rec_by_producto.get(producto_id, 0))
                qty_max_rec = (qty_rec * qty_factor).quantize(Decimal("0.01"))
                if qty_rec <= 0:
                    raise ConflictError("El documento incluye productos que no existen en la recepcion asociada.")

                consumido_rec = (
                    DocumentoCompraProveedorItem.all_objects
                    .filter(
                        empresa=documento.empresa,
                        documento__recepcion_compra=recepcion,
                        documento__estado=EstadoDocumentoCompra.CONFIRMADO,
                        producto_id=producto_id,
                    )
                    .exclude(documento_id=documento.id)
                    .aggregate(total=Sum("cantidad"))
                    .get("total")
                    or Decimal("0")
                )
                if (Decimal(consumido_rec) + qty_actual) > qty_max_rec:
                    raise ConflictError(
                        "La cantidad del documento supera lo recibido para la recepcion asociada."
                    )

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

        DocumentoCompraService._validar_three_way_match(documento=documento, items=items)

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

        DocumentoCompraService._validar_three_way_match(documento=documento, items=items)

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
