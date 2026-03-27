from django.db import transaction

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.services import DomainEventService, OutboxService
from apps.inventario.models import StockLote, StockSerie
from apps.inventario.services.inventario_service import InventarioService


class LoteService:
    """Servicio administrativo para correcciones seguras de lotes de inventario."""

    source = "inventario.lote_service"

    @staticmethod
    def _get_lote(*, lote_id, empresa):
        """Obtiene un lote del tenant con lock pesimista para correcciones administrativas."""
        lote = (
            StockLote.all_objects.select_for_update()
            .select_related("producto", "bodega")
            .filter(id=lote_id, empresa=empresa)
            .first()
        )
        if not lote:
            raise ResourceNotFoundError("Lote no encontrado.")
        return lote

    @staticmethod
    def _record_side_effects(*, empresa, usuario, event_name, summary, lote, payload, aggregate_id=None):
        """Registra trazabilidad enterprise para correcciones administrativas de lotes."""
        aggregate_id = aggregate_id or lote.id
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="STOCK_LOTE",
            aggregate_id=aggregate_id,
            event_type=event_name,
            payload=payload,
            meta={"source": LoteService.source},
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="inventario.lotes",
            event_name=event_name,
            payload=payload,
            usuario=usuario,
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code=Modulos.INVENTARIO,
            action_code=Acciones.EDITAR,
            event_type=event_name.upper().replace(".", "_"),
            entity_type="STOCK_LOTE",
            entity_id=str(aggregate_id),
            summary=summary,
            severity=AuditSeverity.WARNING,
            changes={},
            payload=payload,
            source=LoteService.source,
        )

    @classmethod
    @transaction.atomic
    def corregir_codigo(cls, *, lote_id, empresa, usuario, nuevo_codigo, motivo):
        """Corrige o fusiona un lote existente preservando stock, series y trazabilidad auditada."""
        lote = cls._get_lote(lote_id=lote_id, empresa=empresa)
        nuevo_codigo = str(nuevo_codigo or "").strip().upper()
        motivo = str(motivo or "").strip()

        if not nuevo_codigo:
            raise BusinessRuleError("Debe informar el nuevo codigo de lote.")
        if not motivo:
            raise BusinessRuleError("Debe informar el motivo de la correccion.")
        if nuevo_codigo == lote.lote_codigo:
            raise BusinessRuleError("El nuevo codigo de lote debe ser distinto al actual.")

        destino = (
            StockLote.all_objects.select_for_update()
            .filter(
                empresa=empresa,
                producto=lote.producto,
                bodega=lote.bodega,
                lote_codigo=nuevo_codigo,
            )
            .first()
        )

        if not destino:
            canonico = InventarioService._canonicalizar_lote_para_similitud(nuevo_codigo)
            similares = sorted(
                {
                    codigo
                    for codigo in StockLote.all_objects.filter(
                        empresa=empresa,
                        producto=lote.producto,
                        bodega=lote.bodega,
                    ).exclude(id=lote.id).values_list("lote_codigo", flat=True)
                    if InventarioService._canonicalizar_lote_para_similitud(codigo) == canonico
                }
            )
            if similares:
                sugerencias = ", ".join(similares[:3])
                raise BusinessRuleError(
                    f"El lote {nuevo_codigo} es muy similar a un lote existente para {lote.producto.nombre}: {sugerencias}. Revise si corresponde usar el lote ya registrado."
                )

        stock_origen = lote.stock
        codigo_origen = lote.lote_codigo
        vencimiento_origen = lote.fecha_vencimiento

        if destino:
            if (
                destino.fecha_vencimiento
                and lote.fecha_vencimiento
                and destino.fecha_vencimiento != lote.fecha_vencimiento
            ):
                raise ConflictError(
                    f"El lote destino {nuevo_codigo} ya existe con vencimiento {destino.fecha_vencimiento:%d/%m/%Y}."
                )

            if destino.fecha_vencimiento is None and lote.fecha_vencimiento is not None:
                destino.fecha_vencimiento = lote.fecha_vencimiento

            destino.stock = destino.stock + lote.stock
            destino.save(update_fields=["stock", "fecha_vencimiento", "actualizado_en"])

            StockSerie.all_objects.filter(
                empresa=empresa,
                producto=lote.producto,
                bodega=lote.bodega,
                lote_codigo=codigo_origen,
            ).update(lote_codigo=nuevo_codigo)

            lote.producto.movimientos.filter(
                empresa=empresa,
                bodega=lote.bodega,
                lote_codigo=codigo_origen,
            ).update(lote_codigo=nuevo_codigo)

            lote.delete()
            lote_objetivo = destino
            accion = "fusionado"
        else:
            StockSerie.all_objects.filter(
                empresa=empresa,
                producto=lote.producto,
                bodega=lote.bodega,
                lote_codigo=codigo_origen,
            ).update(lote_codigo=nuevo_codigo)

            lote.producto.movimientos.filter(
                empresa=empresa,
                bodega=lote.bodega,
                lote_codigo=codigo_origen,
            ).update(lote_codigo=nuevo_codigo)

            lote.lote_codigo = nuevo_codigo
            lote.save(update_fields=["lote_codigo", "actualizado_en"])
            lote_objetivo = lote
            accion = "renombrado"

        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            event_name="inventario.lote.codigo_corregido",
            summary=f"Lote {codigo_origen} corregido a {nuevo_codigo} para {lote.producto.nombre}.",
            lote=lote_objetivo,
            payload={
                "lote_id": str(lote_objetivo.id),
                "producto_id": str(lote.producto_id),
                "bodega_id": str(lote.bodega_id),
                "codigo_anterior": codigo_origen,
                "codigo_nuevo": nuevo_codigo,
                "vencimiento": vencimiento_origen.isoformat() if vencimiento_origen else None,
                "stock_afectado": str(stock_origen),
                "motivo": motivo,
                "accion": accion,
            },
        )
        return lote_objetivo

    @classmethod
    @transaction.atomic
    def anular_lote(cls, *, lote_id, empresa, usuario, motivo):
        """Anula un lote sin stock ni series disponibles para limpiar errores de digitacion sin tocar stock."""
        lote = cls._get_lote(lote_id=lote_id, empresa=empresa)
        motivo = str(motivo or "").strip()
        if not motivo:
            raise BusinessRuleError("Debe informar el motivo de la anulacion.")
        if lote.stock != 0:
            raise ConflictError("Solo se pueden anular lotes sin stock.")

        series_disponibles = StockSerie.all_objects.filter(
            empresa=empresa,
            producto=lote.producto,
            bodega=lote.bodega,
            lote_codigo=lote.lote_codigo,
            estado="DISPONIBLE",
        ).exists()
        if series_disponibles:
            raise ConflictError("No se puede anular un lote con series disponibles.")

        payload = {
            "lote_id": str(lote.id),
            "producto_id": str(lote.producto_id),
            "bodega_id": str(lote.bodega_id),
            "codigo": lote.lote_codigo,
            "vencimiento": lote.fecha_vencimiento.isoformat() if lote.fecha_vencimiento else None,
            "motivo": motivo,
        }
        lote_id = lote.id
        lote.delete()
        cls._record_side_effects(
            empresa=empresa,
            usuario=usuario,
            event_name="inventario.lote.anulado",
            summary=f"Lote {payload['codigo']} anulado para {lote.producto.nombre}.",
            lote=lote,
            payload=payload,
            aggregate_id=lote_id,
        )

    @staticmethod
    def listar_lotes(*, empresa, producto_id=None, bodega_id=None):
        """Lista lotes operativos para seleccion y correccion administrativa."""
        queryset = StockLote.all_objects.filter(empresa=empresa).select_related("producto", "bodega")
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        if bodega_id:
            queryset = queryset.filter(bodega_id=bodega_id)
        return queryset.order_by("producto__nombre", "bodega__nombre", "lote_codigo")
