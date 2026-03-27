from decimal import Decimal
import hashlib
import json
from uuid import uuid4
from django.db import transaction
from apps.core.exceptions import BusinessRuleError, ResourceNotFoundError
from apps.core.validators import normalizar_texto
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models.bodega import Bodega
from apps.inventario.models.inventario_snapshot import InventorySnapshot
from apps.inventario.models.reserva_stock import ReservaStock
from apps.inventario.models.stock_lote import StockLote
from apps.inventario.models.stock_serie import EstadoSerie, StockSerie
from apps.productos.models.producto import Producto
from apps.core.services.domain_event_service import DomainEventService
from apps.core.services.outbox_service import OutboxService
from apps.auditoria.services import AuditoriaService
from apps.auditoria.models import AuditSeverity
from apps.inventario.models.movimiento import MovimientoInventario, TipoMovimiento
from apps.inventario.models.stock_producto import StockProducto
from apps.core.permisos.constantes_permisos import Modulos, Acciones


class InventarioService:
    @staticmethod
    def _record_reserva_side_effects(*, empresa, usuario, event_name, summary, aggregate_id, entity_id, payload, changes):
        """Registra trazabilidad enterprise para reservas y liberaciones de stock."""
        if not usuario:
            return

        payload_fingerprint = hashlib.sha1(
            json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        dedup_key = f"invres:{event_name}:{aggregate_id}:{payload_fingerprint}"[:120]
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="RESERVA_STOCK",
            aggregate_id=aggregate_id,
            event_type=event_name,
            payload=payload,
            meta={"source": "InventarioService.reservas"},
            usuario=usuario,
            idempotency_key=dedup_key,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="inventario.reservas",
            event_name=event_name,
            payload=payload,
            usuario=usuario,
            dedup_key=dedup_key,
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=Modulos.INVENTARIO,
            action_code=Acciones.EDITAR,
            event_type=event_name,
            entity_type="RESERVA_STOCK",
            entity_id=str(entity_id),
            summary=summary,
            severity=AuditSeverity.INFO,
            changes=changes,
            payload=payload,
            meta={"source": "InventarioService.reservas"},
            source="InventarioService.reservas",
            idempotency_key=f"audit:{dedup_key}",
        )


    @staticmethod
    def _money(value):
        """Normaliza montos monetarios a 2 decimales."""
        return Decimal(value).quantize(Decimal("0.01"))

    @staticmethod
    def _cost(value):
        """Normaliza costos unitarios a 4 decimales."""
        return Decimal(value).quantize(Decimal("0.0001"))

    @staticmethod
    def _serialize_decimal(value, *, decimals="0.01"):
        """Serializa decimales a string estable para payloads y auditoria."""
        return str(Decimal(value).quantize(Decimal(decimals)))

    @staticmethod
    def _resolver_costo_base_producto(producto):
        """Obtiene el costo base del producto usando costo promedio o precio costo como respaldo."""
        costo_promedio = Decimal(producto.costo_promedio or 0)
        if costo_promedio > 0:
            return InventarioService._cost(costo_promedio)

        precio_costo = Decimal(producto.precio_costo or 0)
        return InventarioService._cost(precio_costo)

    @staticmethod
    def _validar_cantidad_producto(*, producto, cantidad, field_name="cantidad"):
        """Aplica reglas de fraccionamiento definidas en el maestro del producto."""
        cantidad = Decimal(cantidad)
        if producto.permite_decimales:
            return cantidad

        if cantidad != cantidad.quantize(Decimal("1")):
            raise BusinessRuleError(
                f"El producto {producto.nombre} no permite {field_name} fraccionada."
            )

        return cantidad

    @staticmethod
    def _normalizar_series(series):
        """Normaliza codigos de serie y elimina vacios para trazabilidad."""
        if not series:
            return []

        normalizadas = []
        for serie in series:
            valor = str(serie or "").strip().upper()
            if valor:
                normalizadas.append(valor)
        return normalizadas

    @staticmethod
    def _validar_trazabilidad_producto(*, producto, tipo, cantidad, lote_codigo, series, fecha_vencimiento):
        """Valida reglas de lotes, series y vencimiento segun configuracion del producto."""
        series = InventarioService._normalizar_series(series)

        if producto.usa_lotes and not lote_codigo:
            raise BusinessRuleError(
                f"El producto {producto.nombre} requiere lote para registrar movimientos."
            )

        if fecha_vencimiento and not producto.usa_vencimiento:
            raise BusinessRuleError(
                f"El producto {producto.nombre} no tiene control de vencimiento habilitado."
            )

        if producto.usa_series:
            if cantidad != cantidad.quantize(Decimal("1")):
                raise BusinessRuleError(
                    f"El producto {producto.nombre} con series requiere cantidad entera."
                )

            if not series:
                raise BusinessRuleError(
                    f"El producto {producto.nombre} requiere codigos de serie para el movimiento."
                )

            if len(series) != int(cantidad):
                raise BusinessRuleError(
                    f"La cantidad de series ({len(series)}) no coincide con la cantidad ({int(cantidad)})."
                )

            if len(set(series)) != len(series):
                raise BusinessRuleError("No se permiten series duplicadas en el mismo movimiento.")

        elif series:
            raise BusinessRuleError(
                f"El producto {producto.nombre} no utiliza control por series."
            )

        return series

    @staticmethod
    def _aplicar_trazabilidad_lote(*, empresa, producto, bodega_id, tipo, cantidad, lote_codigo, fecha_vencimiento):
        """Actualiza stock por lote para mantener trazabilidad operativa."""
        if not lote_codigo:
            return

        lote_stock, _ = StockLote.all_objects.select_for_update().get_or_create(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
            lote_codigo=lote_codigo,
            defaults={
                "fecha_vencimiento": fecha_vencimiento,
                "stock": Decimal("0"),
            },
        )

        if fecha_vencimiento and lote_stock.fecha_vencimiento is None:
            lote_stock.fecha_vencimiento = fecha_vencimiento

        if tipo == TipoMovimiento.ENTRADA:
            lote_stock.stock = Decimal(lote_stock.stock) + Decimal(cantidad)
        else:
            if Decimal(lote_stock.stock) < Decimal(cantidad):
                raise BusinessRuleError(
                    f"Stock insuficiente en lote {lote_codigo} para {producto.nombre}."
                )
            lote_stock.stock = Decimal(lote_stock.stock) - Decimal(cantidad)

        lote_stock.save(update_fields=["stock", "fecha_vencimiento"])

    @staticmethod
    def _aplicar_trazabilidad_series(
        *,
        empresa,
        producto,
        bodega_id,
        tipo,
        movimiento,
        lote_codigo,
        fecha_vencimiento,
        series,
    ):
        """Registra series en entrada y las marca en salida para auditoria unitaria."""
        if not series:
            return

        if tipo == TipoMovimiento.ENTRADA:
            existentes = set(
                StockSerie.all_objects.filter(
                    empresa=empresa,
                    producto=producto,
                    serie_codigo__in=series,
                ).values_list("serie_codigo", flat=True)
            )
            if existentes:
                codigos = ", ".join(sorted(existentes))
                raise BusinessRuleError(f"Ya existen series registradas para {producto.nombre}: {codigos}.")

            StockSerie.all_objects.bulk_create(
                [
                    StockSerie(
                        empresa=empresa,
                        creado_por=movimiento.creado_por,
                        producto=producto,
                        bodega_id=bodega_id,
                        serie_codigo=serie_codigo,
                        lote_codigo=lote_codigo or "",
                        fecha_vencimiento=fecha_vencimiento,
                        estado=EstadoSerie.DISPONIBLE,
                        movimiento_entrada=movimiento,
                    )
                    for serie_codigo in series
                ]
            )
            return

        series_stock = list(
            StockSerie.all_objects.select_for_update().filter(
                empresa=empresa,
                producto=producto,
                bodega_id=bodega_id,
                serie_codigo__in=series,
            )
        )

        mapeo = {row.serie_codigo: row for row in series_stock}
        faltantes = [serie for serie in series if serie not in mapeo]
        if faltantes:
            raise BusinessRuleError(
                f"No existen series en bodega para {producto.nombre}: {', '.join(sorted(faltantes))}."
            )

        for serie in series:
            registro = mapeo[serie]
            if registro.estado != EstadoSerie.DISPONIBLE:
                raise BusinessRuleError(
                    f"La serie {serie} no esta disponible para salida en {producto.nombre}."
                )
            registro.estado = EstadoSerie.SALIDA
            registro.movimiento_salida = movimiento
            registro.save(update_fields=["estado", "movimiento_salida"])

    @staticmethod
    def _resolver_bodega_id(*, empresa, bodega_id):
        """Resuelve bodega valida o crea la bodega principal por defecto."""
        if bodega_id:
            existe = Bodega.all_objects.filter(id=bodega_id, empresa=empresa, activa=True).exists()
            if not existe:
                raise BusinessRuleError("La bodega seleccionada no existe o no esta activa.")
            return bodega_id

        nombre_bodega_principal = normalizar_texto("Principal")
        bodega_default, _ = Bodega.all_objects.get_or_create(
            empresa=empresa,
            nombre=nombre_bodega_principal,
            defaults={"activa": True},
        )
        return bodega_default.id

    @staticmethod
    def _obtener_producto_con_lock(*, empresa, producto_id, context):
        """Obtiene un producto inventariable con lock pesimista o levanta un not found del dominio."""
        producto = (
            Producto.all_objects.select_for_update()
            .filter(pk=producto_id, empresa=empresa)
            .first()
        )
        if not producto:
            raise ResourceNotFoundError(f"Producto no encontrado para {context}.")
        return producto

    @staticmethod
    def _validar_documento_reserva(*, documento_tipo, documento_id):
        """Valida metadatos de documento requeridos para reservas trazables."""
        if not documento_tipo or not documento_id:
            raise BusinessRuleError("Las reservas requieren documento_tipo y documento_id.")
        if documento_tipo not in {valor for valor, _ in TipoDocumentoReferencia.choices}:
            raise BusinessRuleError("Tipo de documento invalido para reserva de stock.")

    @staticmethod
    def _reservado_total(*, empresa, producto, bodega_id):
        """Obtiene el total reservado de un producto en una bodega."""
        reservas = ReservaStock.all_objects.filter(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
        )
        total = Decimal("0")
        for reserva in reservas.only("cantidad"):
            total += Decimal(reserva.cantidad)
        return total

    @staticmethod
    def _stock_defaults_para_bodega(*, empresa, producto):
        """Define stock inicial por bodega sin duplicar stock global ya distribuido."""
        existe_stock_por_bodega = StockProducto.all_objects.filter(
            empresa=empresa,
            producto=producto,
        ).exists()
        if existe_stock_por_bodega:
            return {
                "stock": Decimal("0"),
                "valor_stock": Decimal("0"),
            }

        stock_inicial = Decimal(producto.stock_actual)
        return {
            "stock": stock_inicial,
            "valor_stock": InventarioService._money(
                stock_inicial * Decimal(producto.costo_promedio)
            ),
        }

    @staticmethod
    @transaction.atomic
    def reservar_stock(
        *,
        producto_id,
        bodega_id=None,
        cantidad,
        documento_tipo,
        documento_id,
        empresa,
        usuario,
    ):
        """Crea una reserva de stock verificando disponibilidad real."""
        if cantidad <= 0:
            raise BusinessRuleError("La cantidad a reservar debe ser mayor a cero.")

        InventarioService._validar_documento_reserva(
            documento_tipo=documento_tipo,
            documento_id=documento_id,
        )

        cantidad = Decimal(cantidad)
        bodega_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_id)
        producto = InventarioService._obtener_producto_con_lock(
            empresa=empresa,
            producto_id=producto_id,
            context="reserva de inventario",
        )

        if not producto.maneja_inventario:
            raise BusinessRuleError(f"El producto {producto.nombre} no maneja inventario.")

        cantidad = InventarioService._validar_cantidad_producto(
            producto=producto,
            cantidad=cantidad,
            field_name="cantidad reservada",
        )

        stock_obj, _ = StockProducto.all_objects.select_for_update().get_or_create(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
            defaults=InventarioService._stock_defaults_para_bodega(
                empresa=empresa,
                producto=producto,
            ),
        )

        reservado_total = InventarioService._reservado_total(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
        )
        disponible = Decimal(stock_obj.stock) - reservado_total
        if cantidad > disponible:
            raise BusinessRuleError("Stock insuficiente para reservar la cantidad solicitada.")

        reserva = ReservaStock.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            producto=producto,
            bodega_id=bodega_id,
            cantidad=cantidad,
            documento_tipo=documento_tipo,
            documento_id=documento_id,
        )
        payload = {
            "reserva_id": str(reserva.id),
            "producto_id": str(producto.id),
            "bodega_id": str(bodega_id),
            "cantidad": InventarioService._serialize_decimal(cantidad),
            "documento_tipo": documento_tipo,
            "documento_id": str(documento_id),
        }
        InventarioService._record_reserva_side_effects(
            empresa=empresa,
            usuario=usuario,
            event_name="INVENTARIO_RESERVA_CREADA",
            summary=f"Reserva de stock creada para producto {producto.nombre}.",
            aggregate_id=reserva.id,
            entity_id=reserva.id,
            payload=payload,
            changes={
                "cantidad_reservada": ["0.00", InventarioService._serialize_decimal(cantidad)],
            },
        )
        return reserva

    @staticmethod
    @transaction.atomic
    def liberar_reserva(
        *,
        producto_id,
        bodega_id=None,
        documento_tipo,
        documento_id,
        empresa,
        cantidad=None,
        usuario=None,
    ):
        """Libera reservas por documento en forma total o parcial."""
        InventarioService._validar_documento_reserva(
            documento_tipo=documento_tipo,
            documento_id=documento_id,
        )

        bodega_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_id)

        reservas = list(
            ReservaStock.all_objects.select_for_update().filter(
                empresa=empresa,
                producto_id=producto_id,
                bodega_id=bodega_id,
                documento_tipo=documento_tipo,
                documento_id=documento_id,
            ).order_by("creado_en", "id")
        )

        if not reservas:
            return Decimal("0")

        producto = InventarioService._obtener_producto_con_lock(
            empresa=empresa,
            producto_id=producto_id,
            context="liberacion de reserva",
        )

        liberado = Decimal("0")
        if cantidad is None:
            reservas_payload = []
            for reserva in reservas:
                liberado += Decimal(reserva.cantidad)
                reservas_payload.append(
                    {
                        "reserva_id": str(reserva.id),
                        "cantidad": InventarioService._serialize_decimal(reserva.cantidad),
                    }
                )
            for reserva in reservas:
                reserva.delete()
            InventarioService._record_reserva_side_effects(
                empresa=empresa,
                usuario=usuario,
                event_name="INVENTARIO_RESERVA_LIBERADA",
                summary=f"Reserva de stock liberada para producto {producto.nombre}.",
                aggregate_id=producto.id,
                entity_id=producto.id,
                payload={
                    "producto_id": str(producto.id),
                    "bodega_id": str(bodega_id),
                    "documento_tipo": documento_tipo,
                    "documento_id": str(documento_id),
                    "reservas": reservas_payload,
                    "cantidad_liberada": InventarioService._serialize_decimal(liberado),
                },
                changes={
                    "cantidad_reservada": [InventarioService._serialize_decimal(liberado), "0.00"],
                },
            )
            return liberado

        restante = Decimal(cantidad)
        if restante <= 0:
            return Decimal("0")

        restante = InventarioService._validar_cantidad_producto(
            producto=producto,
            cantidad=restante,
            field_name="cantidad a liberar",
        )

        reservas_payload = []
        for reserva in reservas:
            actual = Decimal(reserva.cantidad)
            if restante <= 0:
                break

            if actual <= restante:
                restante -= actual
                liberado += actual
                reservas_payload.append(
                    {
                        "reserva_id": str(reserva.id),
                        "cantidad_antes": InventarioService._serialize_decimal(actual),
                        "cantidad_despues": "0.00",
                    }
                )
                reserva.delete()
                continue

            reserva.cantidad = actual - restante
            reserva.save(update_fields=["cantidad"])
            reservas_payload.append(
                {
                    "reserva_id": str(reserva.id),
                    "cantidad_antes": InventarioService._serialize_decimal(actual),
                    "cantidad_despues": InventarioService._serialize_decimal(reserva.cantidad),
                }
            )
            liberado += restante
            restante = Decimal("0")

        if liberado > 0:
            InventarioService._record_reserva_side_effects(
                empresa=empresa,
                usuario=usuario,
                event_name="INVENTARIO_RESERVA_LIBERADA",
                summary=f"Reserva de stock liberada para producto {producto.nombre}.",
                aggregate_id=producto.id,
                entity_id=producto.id,
                payload={
                    "producto_id": str(producto.id),
                    "bodega_id": str(bodega_id),
                    "documento_tipo": documento_tipo,
                    "documento_id": str(documento_id),
                    "reservas": reservas_payload,
                    "cantidad_liberada": InventarioService._serialize_decimal(liberado),
                },
                changes={
                    "cantidad_liberada": ["0.00", InventarioService._serialize_decimal(liberado)],
                },
            )
        return liberado

    @staticmethod
    @transaction.atomic
    def registrar_movimiento(
        *,
        producto_id,
        bodega_id=None,
        tipo,
        cantidad,
        referencia,
        empresa,
        usuario,
        costo_unitario=None,
        documento_tipo=None,
        documento_id=None,
        lote_codigo="",
        fecha_vencimiento=None,
        series=None,
    ):
        """Registra un movimiento de inventario con valorizacion y trazabilidad."""

        if cantidad <= 0:
            raise BusinessRuleError("La cantidad debe ser mayor a cero.")

        cantidad = Decimal(cantidad)

        if tipo not in {TipoMovimiento.ENTRADA, TipoMovimiento.SALIDA}:
            raise BusinessRuleError("Tipo de movimiento invalido.")

        if costo_unitario is not None and Decimal(costo_unitario) < 0:
            raise BusinessRuleError("El costo unitario no puede ser negativo.")

        bodega_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_id)

        producto = InventarioService._obtener_producto_con_lock(
            empresa=empresa,
            producto_id=producto_id,
            context="movimiento de inventario",
        )

        cantidad = InventarioService._validar_cantidad_producto(
            producto=producto,
            cantidad=cantidad,
            field_name="cantidad de movimiento",
        )
        lote_codigo = str(lote_codigo or "").strip().upper()
        series = InventarioService._validar_trazabilidad_producto(
            producto=producto,
            tipo=tipo,
            cantidad=cantidad,
            lote_codigo=lote_codigo,
            series=series,
            fecha_vencimiento=fecha_vencimiento,
        )

        if not producto.maneja_inventario:
            raise BusinessRuleError(
                f"El producto {producto.nombre} no maneja inventario."
            )

        stock_obj, _ = (
            StockProducto.all_objects
            .select_for_update()
            .get_or_create(
                empresa=empresa,
                producto=producto,
                bodega_id=bodega_id,
                defaults=InventarioService._stock_defaults_para_bodega(
                    empresa=empresa,
                    producto=producto,
                )
            )
        )

        stock_anterior = Decimal(stock_obj.stock)
        valor_stock_anterior = InventarioService._money(stock_obj.valor_stock)
        costo_promedio_anterior = InventarioService._cost(producto.costo_promedio or 0)
        stock_global_anterior = Decimal(producto.stock_actual or 0)
        reserva_consumible = Decimal("0")
        reservado_total = Decimal("0")
        if tipo == TipoMovimiento.SALIDA:
            reservado_total = InventarioService._reservado_total(
                empresa=empresa,
                producto=producto,
                bodega_id=bodega_id,
            )
            if documento_tipo and documento_id:
                reservas_doc = ReservaStock.all_objects.filter(
                    empresa=empresa,
                    producto=producto,
                    bodega_id=bodega_id,
                    documento_tipo=documento_tipo,
                    documento_id=documento_id,
                )
                for reserva in reservas_doc.only("cantidad"):
                    reserva_consumible += Decimal(reserva.cantidad)

        if tipo == TipoMovimiento.ENTRADA:
            nuevo_stock = stock_anterior + cantidad

        else:
            # Disponibilidad real = stock - reservas de otros documentos.
            reservado_otros = max(Decimal("0"), reservado_total - reserva_consumible)
            disponible_para_salida = stock_anterior - reservado_otros
            if cantidad > disponible_para_salida:
                raise BusinessRuleError(
                    f"Stock insuficiente para {producto.nombre}: disponible {disponible_para_salida}."
                )

            nuevo_stock = stock_anterior - cantidad

            if nuevo_stock < 0:
                raise BusinessRuleError(
                    f"Stock insuficiente para {producto.nombre}"
                )

        # En el primer ingreso sin historial usamos el costo del maestro para no valorizar a cero.
        costo_movimiento = (
            Decimal(costo_unitario)
            if costo_unitario is not None
            else InventarioService._resolver_costo_base_producto(producto)
        )
        costo_movimiento = InventarioService._cost(costo_movimiento)

        valor_total = InventarioService._money(Decimal(cantidad) * Decimal(costo_movimiento))

        if tipo == TipoMovimiento.ENTRADA:
            valor_stock_nuevo = InventarioService._money(valor_stock_anterior + valor_total)
        else:
            valor_stock_nuevo = InventarioService._money(valor_stock_anterior - valor_total)
            if valor_stock_nuevo < 0:
                valor_stock_nuevo = InventarioService._money(Decimal("0"))

        if nuevo_stock > 0:
            producto.costo_promedio = InventarioService._cost(valor_stock_nuevo / Decimal(nuevo_stock))
        else:
            producto.costo_promedio = InventarioService._cost(Decimal("0"))

        if documento_tipo and documento_tipo not in {valor for valor, _ in TipoDocumentoReferencia.choices}:
            raise BusinessRuleError("Tipo de documento invalido para inventario.")

        movimiento = MovimientoInventario.all_objects.create(
            producto=producto,
            bodega_id=bodega_id,
            tipo=tipo,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            costo_unitario=costo_movimiento,
            valor_total=valor_total,
            lote_codigo=lote_codigo,
            fecha_vencimiento=fecha_vencimiento,
            series_codigos=series,
            documento_tipo=documento_tipo,
            documento_id=documento_id,
            referencia=referencia,
            empresa=empresa,
            creado_por=usuario
        )

        InventarioService._aplicar_trazabilidad_lote(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
            tipo=tipo,
            cantidad=cantidad,
            lote_codigo=lote_codigo,
            fecha_vencimiento=fecha_vencimiento,
        )
        InventarioService._aplicar_trazabilidad_series(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
            tipo=tipo,
            movimiento=movimiento,
            lote_codigo=lote_codigo,
            fecha_vencimiento=fecha_vencimiento,
            series=series,
        )

        stock_obj.stock = nuevo_stock
        stock_obj.valor_stock = valor_stock_nuevo
        stock_obj.save(update_fields=["stock", "valor_stock"])

        InventorySnapshot.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            producto=producto,
            bodega_id=bodega_id,
            movimiento=movimiento,
            stock=stock_obj.stock,
            costo_promedio=InventarioService._cost(producto.costo_promedio),
            valor_stock=stock_obj.valor_stock,
        )

        if tipo == TipoMovimiento.ENTRADA:
            producto.stock_actual += cantidad
        else:
            producto.stock_actual -= cantidad

            # Consumimos reserva vinculada al mismo documento para evitar sobre-reserva.
            if documento_tipo and documento_id and reserva_consumible > 0:
                InventarioService.liberar_reserva(
                    producto_id=producto.id,
                    bodega_id=bodega_id,
                    documento_tipo=documento_tipo,
                    documento_id=documento_id,
                    empresa=empresa,
                    cantidad=min(cantidad, reserva_consumible),
                    usuario=usuario,
                )

        producto.save(
            skip_clean=True,
            update_fields=["stock_actual", "costo_promedio"]
        )

        stock_global_nuevo = Decimal(producto.stock_actual or 0)

        payload = {
            "movimiento_id": str(movimiento.id),
            "producto_id": str(producto.id),
            "bodega_id": str(bodega_id),
            "tipo": tipo,
            "cantidad": InventarioService._serialize_decimal(cantidad),
            "stock_anterior": InventarioService._serialize_decimal(stock_anterior),
            "stock_nuevo": InventarioService._serialize_decimal(nuevo_stock),
            "stock_global_anterior": InventarioService._serialize_decimal(stock_global_anterior),
            "stock_global_nuevo": InventarioService._serialize_decimal(stock_global_nuevo),
            "valor_stock_anterior": InventarioService._serialize_decimal(valor_stock_anterior),
            "valor_stock_nuevo": InventarioService._serialize_decimal(valor_stock_nuevo),
            "costo_promedio_anterior": InventarioService._serialize_decimal(
                costo_promedio_anterior,
                decimals="0.0001",
            ),
            "costo_promedio_nuevo": InventarioService._serialize_decimal(
                producto.costo_promedio,
                decimals="0.0001",
            ),
            "costo_unitario": InventarioService._serialize_decimal(costo_movimiento, decimals="0.0001"),
            "valor_total": InventarioService._serialize_decimal(valor_total),
            "lote_codigo": lote_codigo,
            "series": series,
            "documento_tipo": documento_tipo,
            "documento_id": str(documento_id) if documento_id else None,
            "reserva_consumida": InventarioService._serialize_decimal(reserva_consumible),
        }
        changes = {
            "stock_bodega": [
                InventarioService._serialize_decimal(stock_anterior),
                InventarioService._serialize_decimal(nuevo_stock),
            ],
            "stock_global_producto": [
                InventarioService._serialize_decimal(stock_global_anterior),
                InventarioService._serialize_decimal(stock_global_nuevo),
            ],
            "valor_stock_bodega": [
                InventarioService._serialize_decimal(valor_stock_anterior),
                InventarioService._serialize_decimal(valor_stock_nuevo),
            ],
            "costo_promedio_producto": [
                InventarioService._serialize_decimal(costo_promedio_anterior, decimals="0.0001"),
                InventarioService._serialize_decimal(producto.costo_promedio, decimals="0.0001"),
            ],
        }
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="INVENTARIO",
            aggregate_id=movimiento.id,
            event_type="INVENTARIO_MOVIMIENTO_REGISTRADO",
            payload=payload,
            meta={"source": "InventarioService.registrar_movimiento"},
            usuario=usuario,
            idempotency_key=f"inventario-mov:{movimiento.id}",
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="inventario",
            event_name="INVENTARIO_MOVIMIENTO_REGISTRADO",
            payload=payload,
            usuario=usuario,
            dedup_key=f"inventario-mov:{movimiento.id}",
        )

        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=Modulos.INVENTARIO,
            action_code=Acciones.EDITAR,
            event_type="INVENTARIO_MOVIMIENTO_REGISTRADO",
            entity_type="MOVIMIENTO_INVENTARIO",
            entity_id=str(movimiento.id),
            summary=f"Movimiento {tipo} registrado para producto {producto.nombre}.",
            severity=AuditSeverity.INFO,
            changes=changes,
            payload=payload,
            meta={"source": "InventarioService.registrar_movimiento"},
            source="InventarioService.registrar_movimiento",
            idempotency_key=f"audit:inventario-mov:{movimiento.id}",
        )

        return movimiento

    @staticmethod
    def obtener_kardex(
        *,
        empresa,
        producto_id,
        bodega_id=None,
        desde=None,
        hasta=None,
        tipo=None,
        documento_tipo=None,
        referencia=None,
    ):
        """Consulta el kardex de movimientos aplicando filtros operativos."""
        queryset = MovimientoInventario.all_objects.filter(empresa=empresa, producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        if desde is not None:
            queryset = queryset.filter(creado_en__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(creado_en__lte=hasta)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if documento_tipo:
            if isinstance(documento_tipo, (list, tuple, set)):
                tipos = [str(valor).strip() for valor in documento_tipo if str(valor).strip()]
            else:
                tipos = [valor.strip() for valor in str(documento_tipo).split(",") if valor.strip()]

            if TipoDocumentoReferencia.COMPRA_RECEPCION in tipos:
                tipos = list(
                    set(tipos).union(
                        {
                            TipoDocumentoReferencia.COMPRA_RECEPCION,
                            TipoDocumentoReferencia.GUIA_RECEPCION,
                            TipoDocumentoReferencia.FACTURA_COMPRA,
                        }
                    )
                )

            queryset = queryset.filter(documento_tipo__in=tipos)
        if referencia:
            queryset = queryset.filter(referencia__icontains=referencia)
        return queryset.order_by("creado_en", "id")

    @staticmethod
    def obtener_snapshot(*, empresa, producto_id, bodega_id, hasta=None):
        """Retorna el ultimo snapshot historico para producto/bodega."""
        queryset = InventorySnapshot.all_objects.filter(
            empresa=empresa,
            producto_id=producto_id,
            bodega_id=bodega_id,
        )
        if hasta is not None:
            queryset = queryset.filter(creado_en__lte=hasta)
        return queryset.order_by("-creado_en", "-id").first()

    @staticmethod
    @transaction.atomic
    def regularizar_stock(
        *,
        producto_id,
        stock_objetivo,
        referencia,
        empresa,
        usuario,
        bodega_id=None,
        costo_unitario=None,
        lote_codigo="",
        fecha_vencimiento=None,
        series=None,
        documento_tipo=TipoDocumentoReferencia.AJUSTE,
        documento_id=None,
    ):
        """Ajusta una bodega a stock objetivo preservando reservas y trazabilidad."""
        stock_objetivo = Decimal(stock_objetivo)
        if stock_objetivo < 0:
            raise BusinessRuleError("El stock objetivo no puede ser negativo.")

        bodega_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_id)
        producto = Producto.all_objects.select_for_update().filter(pk=producto_id, empresa=empresa).first()
        if not producto:
            raise ResourceNotFoundError("Producto no encontrado para regularizacion de inventario.")
        stock_obj, _ = StockProducto.all_objects.select_for_update().get_or_create(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
            defaults=InventarioService._stock_defaults_para_bodega(
                empresa=empresa,
                producto=producto,
            ),
        )

        stock_actual_bodega = Decimal(stock_obj.stock)
        stock_objetivo = InventarioService._validar_cantidad_producto(
            producto=producto,
            cantidad=stock_objetivo,
            field_name="stock objetivo",
        )

        reservado_total = InventarioService._reservado_total(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
        )
        if stock_objetivo < reservado_total:
            raise BusinessRuleError(
                "No se puede regularizar por debajo del stock reservado en la bodega."
            )

        diferencia = stock_objetivo - stock_actual_bodega
        if diferencia == 0:
            raise BusinessRuleError("El stock objetivo coincide con el stock actual de la bodega.")

        tipo = TipoMovimiento.ENTRADA if diferencia > 0 else TipoMovimiento.SALIDA
        return InventarioService.registrar_movimiento(
            producto_id=producto_id,
            bodega_id=bodega_id,
            tipo=tipo,
            cantidad=abs(diferencia),
            referencia=referencia,
            empresa=empresa,
            usuario=usuario,
            costo_unitario=costo_unitario,
            documento_tipo=documento_tipo,
            documento_id=documento_id,
            lote_codigo=lote_codigo,
            fecha_vencimiento=fecha_vencimiento,
            series=series,
        )

    @staticmethod
    def previsualizar_regularizacion_stock(*, producto_id, stock_objetivo, empresa, bodega_id=None):
        """Calcula impacto de un conteo fisico antes de aplicar el ajuste."""
        stock_objetivo = Decimal(stock_objetivo)
        if stock_objetivo < 0:
            raise BusinessRuleError("El stock objetivo no puede ser negativo.")

        bodega_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_id)
        producto = Producto.all_objects.filter(pk=producto_id, empresa=empresa).first()
        if not producto:
            raise ResourceNotFoundError("Producto no encontrado para previsualizacion de inventario.")

        stock_obj, _ = StockProducto.all_objects.get_or_create(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
            defaults=InventarioService._stock_defaults_para_bodega(
                empresa=empresa,
                producto=producto,
            ),
        )

        stock_actual_bodega = Decimal(stock_obj.stock)
        stock_objetivo = InventarioService._validar_cantidad_producto(
            producto=producto,
            cantidad=stock_objetivo,
            field_name="stock objetivo",
        )
        reservado_total = InventarioService._reservado_total(
            empresa=empresa,
            producto=producto,
            bodega_id=bodega_id,
        )
        diferencia = stock_objetivo - stock_actual_bodega
        warnings = []
        ajustable = True

        if diferencia == 0:
            warnings.append("El stock contado coincide con el stock actual.")

        if stock_objetivo < reservado_total:
            ajustable = False
            warnings.append("El stock objetivo queda por debajo del reservado actual.")

        if diferencia > 0:
            tipo_movimiento = TipoMovimiento.ENTRADA
        elif diferencia < 0:
            tipo_movimiento = TipoMovimiento.SALIDA
        else:
            tipo_movimiento = None

        return {
            "producto_id": str(producto.id),
            "producto_nombre": producto.nombre,
            "bodega_id": str(bodega_id),
            "stock_actual": stock_actual_bodega,
            "stock_objetivo": stock_objetivo,
            "diferencia": diferencia,
            "reservado_total": reservado_total,
            "disponible_actual": stock_actual_bodega - reservado_total,
            "tipo_movimiento": tipo_movimiento,
            "ajustable": ajustable,
            "warnings": warnings,
        }

    @staticmethod
    @transaction.atomic
    def trasladar_stock(
        *,
        producto_id,
        bodega_origen_id,
        bodega_destino_id,
        cantidad,
        referencia,
        empresa,
        usuario,
        lote_codigo="",
        documento_tipo=TipoDocumentoReferencia.TRASLADO,
        documento_id=None,
    ):
        """Traslada stock entre bodegas preservando trazabilidad y stock global."""
        cantidad = Decimal(cantidad)
        if cantidad <= 0:
            raise BusinessRuleError("La cantidad a trasladar debe ser mayor a cero.")
        if str(bodega_origen_id) == str(bodega_destino_id):
            raise BusinessRuleError("La bodega origen y destino deben ser distintas.")

        producto = Producto.all_objects.select_for_update().filter(pk=producto_id, empresa=empresa).first()
        if not producto:
            raise ResourceNotFoundError("Producto no encontrado para traslado de inventario.")
        if producto.usa_series:
            raise BusinessRuleError(
                f"El producto {producto.nombre} con series requiere un flujo de traslado unitario especializado."
            )

        bodega_origen_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_origen_id)
        bodega_destino_id = InventarioService._resolver_bodega_id(empresa=empresa, bodega_id=bodega_destino_id)
        cantidad = InventarioService._validar_cantidad_producto(
            producto=producto,
            cantidad=cantidad,
            field_name="cantidad a trasladar",
        )

        traslado_id = str(documento_id or uuid4())
        referencia_origen = f"{referencia} [SALIDA]"
        referencia_destino = f"{referencia} [ENTRADA]"

        movimiento_salida = InventarioService.registrar_movimiento(
            producto_id=producto_id,
            bodega_id=bodega_origen_id,
            tipo=TipoMovimiento.SALIDA,
            cantidad=cantidad,
            referencia=referencia_origen,
            empresa=empresa,
            usuario=usuario,
            costo_unitario=producto.costo_promedio,
            documento_tipo=documento_tipo,
            documento_id=traslado_id,
            lote_codigo=lote_codigo,
        )
        movimiento_entrada = InventarioService.registrar_movimiento(
            producto_id=producto_id,
            bodega_id=bodega_destino_id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=cantidad,
            referencia=referencia_destino,
            empresa=empresa,
            usuario=usuario,
            costo_unitario=movimiento_salida.costo_unitario,
            documento_tipo=documento_tipo,
            documento_id=traslado_id,
            lote_codigo=lote_codigo,
        )

        return {
            "traslado_id": traslado_id,
            "movimiento_salida": movimiento_salida,
            "movimiento_entrada": movimiento_entrada,
        }
