from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.compras.models import (
    DocumentoCompraProveedor,
    DocumentoCompraProveedorItem,
    EstadoDocumentoCompra,
    EstadoOrdenCompra,
    OrdenCompra,
    OrdenCompraItem,
    RecepcionCompra,
    EstadoRecepcion,
    TipoDocumentoCompra,
)
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import EstadoCuenta, TipoDocumento
from apps.core.services import CarteraService, SecuenciaService
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

        for producto_id, qty_actual in current_qty_by_producto.items():
            qty_orden = Decimal(oc_by_producto[producto_id]["cantidad"] or 0)
            qty_max = (qty_orden * qty_factor).quantize(Decimal("0.01"))
            # Se valida contra OC por documento individual para permitir traslape GD/Factura
            # sin bloquear la operación; la no-duplicidad física se controla al mover pendiente.
            if qty_actual > qty_max:
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

                if qty_actual > qty_max_rec:
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
    def _actualizar_estado_orden(*, empresa, orden_compra):
        """Recalcula y persiste el estado de la OC comparando fisico recibido vs cantidades comprometidas."""
        if not orden_compra:
            return

        orden_items = list(
            OrdenCompraItem.all_objects.filter(empresa=empresa, orden_compra=orden_compra)
        )
        if not orden_items:
            return

        producto_ids = {str(item.producto_id) for item in orden_items}
        fisico_por_producto = DocumentoCompraService._cantidad_fisica_previa_por_producto(
            empresa=empresa,
            orden_compra=orden_compra,
            producto_ids=producto_ids,
        )

        completos = 0
        con_algo = 0
        for item in orden_items:
            producto_id = str(item.producto_id)
            recibido = fisico_por_producto.get(producto_id, Decimal("0"))
            if recibido > 0:
                con_algo += 1
            if recibido >= Decimal(item.cantidad):
                completos += 1

        if completos == len(orden_items):
            nuevo_estado = EstadoOrdenCompra.RECIBIDA
        elif con_algo > 0:
            nuevo_estado = EstadoOrdenCompra.PARCIAL
        else:
            nuevo_estado = EstadoOrdenCompra.ENVIADA

        OrdenCompra.all_objects.filter(id=orden_compra.id).update(estado=nuevo_estado)

    @staticmethod
    def _cantidades_oc_por_producto(*, empresa, orden_compra):
        """Devuelve cantidad comprometida en OC por producto para controlar pendientes físicos."""
        filas = (
            OrdenCompraItem.all_objects
            .filter(empresa=empresa, orden_compra=orden_compra)
            .values("producto_id")
            .annotate(total=Sum("cantidad"))
        )
        return {
            str(fila["producto_id"]): Decimal(fila["total"] or 0)
            for fila in filas
        }

    @staticmethod
    def _cantidad_fisica_previa_por_producto(*, empresa, orden_compra, producto_ids):
        """Calcula físico ya ingresado por OC usando movimientos netos (entradas - salidas)."""
        if not producto_ids:
            return {}

        doc_ids = list(
            DocumentoCompraProveedor.all_objects
            .filter(empresa=empresa, orden_compra=orden_compra)
            .values_list("id", flat=True)
        )
        recepcion_ids = list(
            RecepcionCompra.all_objects
            .filter(empresa=empresa, orden_compra=orden_compra)
            .values_list("id", flat=True)
        )

        filtro_refs = Q()
        if doc_ids:
            filtro_refs |= (
                Q(documento_tipo=TipoDocumentoReferencia.GUIA_RECEPCION, documento_id__in=doc_ids)
                | Q(documento_tipo=TipoDocumentoReferencia.FACTURA_COMPRA, documento_id__in=doc_ids)
            )
        if recepcion_ids:
            filtro_refs |= Q(documento_tipo=TipoDocumentoReferencia.COMPRA_RECEPCION, documento_id__in=recepcion_ids)

        if not filtro_refs:
            return {}

        movimientos = (
            MovimientoInventario.all_objects
            .filter(
                empresa=empresa,
                producto_id__in=producto_ids,
            )
            .filter(filtro_refs)
            .values("producto_id", "tipo")
            .annotate(total=Sum("cantidad"))
        )

        neto_por_producto = {}
        for fila in movimientos:
            producto_id = str(fila["producto_id"])
            total = Decimal(fila["total"] or 0)
            if fila["tipo"] == TipoMovimiento.ENTRADA:
                neto_por_producto[producto_id] = neto_por_producto.get(producto_id, Decimal("0")) + total
            else:
                neto_por_producto[producto_id] = neto_por_producto.get(producto_id, Decimal("0")) - total

        return {
            producto_id: max(total_neto, Decimal("0"))
            for producto_id, total_neto in neto_por_producto.items()
        }

    @staticmethod
    def _movimientos_entrada_pendiente_por_oc(*, documento, items, empresa, usuario, bodega_id, referencia, documento_tipo):
        """Registra solo el pendiente físico por producto para evitar doble entrada entre GD/Factura."""
        orden_compra = documento.orden_compra
        if not orden_compra:
            for item in items:
                InventarioService.registrar_movimiento(
                    producto_id=item.producto_id,
                    bodega_id=bodega_id,
                    tipo=TipoMovimiento.ENTRADA,
                    cantidad=item.cantidad,
                    referencia=referencia,
                    empresa=empresa,
                    usuario=usuario,
                    costo_unitario=item.precio_unitario,
                    documento_tipo=documento_tipo,
                    documento_id=documento.id,
                )
            return

        producto_ids = {str(item.producto_id) for item in items}
        cantidad_oc_por_producto = DocumentoCompraService._cantidades_oc_por_producto(
            empresa=empresa,
            orden_compra=orden_compra,
        )
        fisico_previo_por_producto = DocumentoCompraService._cantidad_fisica_previa_por_producto(
            empresa=empresa,
            orden_compra=orden_compra,
            producto_ids=producto_ids,
        )

        pendiente_por_producto = {
            producto_id: max(
                Decimal(cantidad_oc_por_producto.get(producto_id, 0))
                - Decimal(fisico_previo_por_producto.get(producto_id, 0)),
                Decimal("0"),
            )
            for producto_id in producto_ids
        }

        # Regla operacional chilena: GD y Factura compiten por el mismo físico.
        # Se mueve solo el pendiente por producto para soportar parciales sin duplicar stock.
        for item in items:
            producto_id = str(item.producto_id)
            pendiente_producto = Decimal(pendiente_por_producto.get(producto_id, 0))
            if pendiente_producto <= 0:
                continue

            cantidad_item = Decimal(item.cantidad or 0)
            cantidad_a_mover = min(cantidad_item, pendiente_producto)
            if cantidad_a_mover <= 0:
                continue

            InventarioService.registrar_movimiento(
                producto_id=item.producto_id,
                bodega_id=bodega_id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=cantidad_a_mover,
                referencia=referencia,
                empresa=empresa,
                usuario=usuario,
                costo_unitario=item.precio_unitario,
                documento_tipo=documento_tipo,
                documento_id=documento.id,
            )

            pendiente_por_producto[producto_id] = max(
                pendiente_producto - cantidad_a_mover,
                Decimal("0"),
            )

    @staticmethod
    @transaction.atomic
    def confirmar_guia(*, documento_id, empresa, usuario, bodega_id=None, en_transito=False):
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

        # Solo mover inventario si NO hay una recepción confirmada vinculada.
        # Si la recepción ya movió el stock físico, la guía es solo un documento de trazabilidad.
        recepcion_vinculada = documento.recepcion_compra
        ya_recibido = (
            recepcion_vinculada is not None
            and recepcion_vinculada.estado == EstadoRecepcion.CONFIRMADA
        )

        if not ya_recibido and not en_transito:
            DocumentoCompraService._movimientos_entrada_pendiente_por_oc(
                documento=documento,
                items=items,
                empresa=empresa,
                usuario=usuario,
                bodega_id=bodega_id,
                referencia=f"GUIA {documento.folio}",
                documento_tipo=TipoDocumentoReferencia.GUIA_RECEPCION,
            )

        documento.estado = EstadoDocumentoCompra.CONFIRMADO
        documento.confirmado_por = usuario
        documento.confirmado_en = timezone.now()
        documento.save(update_fields=["estado", "confirmado_por", "confirmado_en"])
        DocumentoCompraService._actualizar_estado_orden(empresa=empresa, orden_compra=documento.orden_compra)
        return documento

    @staticmethod
    @transaction.atomic
    def confirmar_factura(*, documento_id, empresa, usuario, bodega_id=None, en_transito=False):
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

        # En tránsito: se confirma el documento tributario, pero sin entrada al stock disponible.
        # No se actualiza el estado de la OC porque aún no hay físico en bodega.
        if en_transito:
            documento.estado = EstadoDocumentoCompra.CONFIRMADO
            documento.confirmado_por = usuario
            documento.confirmado_en = timezone.now()
            documento.save(update_fields=["estado", "confirmado_por", "confirmado_en"])
            CarteraService.registrar_cxp_desde_documento_compra(documento=documento, usuario=usuario)
            return documento

        # Determinar si ya existe una entrada física previa para esta compra.
        # En Chile muchos proveedores solo emiten factura (sin guía ni recepción).
        # En ese caso la factura actúa como documento de entrada y debe mover inventario.
        recepcion_vinculada = documento.recepcion_compra
        ya_recibido_por_recepcion = (
            recepcion_vinculada is not None
            and recepcion_vinculada.estado == EstadoRecepcion.CONFIRMADA
        )

        if not ya_recibido_por_recepcion:
            DocumentoCompraService._movimientos_entrada_pendiente_por_oc(
                documento=documento,
                items=items,
                empresa=empresa,
                usuario=usuario,
                bodega_id=bodega_id,
                referencia=f"FACTURA {documento.folio}",
                documento_tipo=TipoDocumentoReferencia.FACTURA_COMPRA,
            )

        documento.estado = EstadoDocumentoCompra.CONFIRMADO
        documento.confirmado_por = usuario
        documento.confirmado_en = timezone.now()
        documento.save(update_fields=["estado", "confirmado_por", "confirmado_en"])
        DocumentoCompraService._actualizar_estado_orden(empresa=empresa, orden_compra=documento.orden_compra)

        # Vincula impacto financiero para tesoreria/cartera futura.
        CarteraService.registrar_cxp_desde_documento_compra(documento=documento, usuario=usuario)
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
        documento.bloquea_duplicado = False
        documento.anulado_por = usuario
        documento.anulado_en = timezone.now()
        documento.save(update_fields=["estado", "bloquea_duplicado", "anulado_por", "anulado_en"])

        cuenta_por_pagar = getattr(documento, "cuenta_por_pagar", None)
        if cuenta_por_pagar:
            cuenta_por_pagar.estado = EstadoCuenta.ANULADA
            cuenta_por_pagar.saldo = Decimal("0")
            cuenta_por_pagar.save(update_fields=["estado", "saldo"])

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
