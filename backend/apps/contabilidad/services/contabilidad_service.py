from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.contabilidad.models import (
    AsientoContable,
    EstadoAsientoContable,
    MovimientoContable,
    OrigenAsientoContable,
    PlanCuenta,
    TipoCuentaContable,
)
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import OutboxEvent, OutboxStatus, TipoDocumento
from apps.core.services import DomainEventService, OutboxService, SecuenciaService
from apps.documentos.models import EstadoContable


class ContabilidadService:
    """Gestiona plan de cuentas, asientos y procesamiento de solicitudes contables."""

    CODIGOS_BASE = {
        "CAJA": ("111100", "Caja", TipoCuentaContable.ACTIVO),
        "BANCO": ("111200", "Bancos", TipoCuentaContable.ACTIVO),
        "CLIENTES": ("112100", "Clientes", TipoCuentaContable.ACTIVO),
        "IVA_CREDITO": ("119200", "IVA Credito Fiscal", TipoCuentaContable.ACTIVO),
        "PROVEEDORES": ("211100", "Proveedores", TipoCuentaContable.PASIVO),
        "IVA_DEBITO": ("213100", "IVA Debito Fiscal", TipoCuentaContable.PASIVO),
        "CAPITAL": ("311100", "Capital", TipoCuentaContable.PATRIMONIO),
        "VENTAS": ("411100", "Ventas", TipoCuentaContable.INGRESO),
        "COMPRAS": ("511100", "Compras y Servicios", TipoCuentaContable.GASTO),
    }

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))

    @staticmethod
    def recalcular_totales(*, asiento):
        """Recalcula totales y marca si el asiento queda cuadrado."""
        movimientos = MovimientoContable.all_objects.filter(empresa=asiento.empresa, asiento=asiento)
        total_debe = sum((ContabilidadService._decimal(mov.debe) for mov in movimientos), Decimal("0.00"))
        total_haber = sum((ContabilidadService._decimal(mov.haber) for mov in movimientos), Decimal("0.00"))
        cuadrado = total_debe == total_haber and total_debe > 0

        AsientoContable.all_objects.filter(id=asiento.id).update(
            total_debe=total_debe,
            total_haber=total_haber,
            cuadrado=cuadrado,
        )
        asiento.total_debe = total_debe
        asiento.total_haber = total_haber
        asiento.cuadrado = cuadrado
        return asiento

    @staticmethod
    def validar_editable(*, asiento):
        """Valida que el asiento siga en borrador antes de aceptar cambios manuales."""
        if asiento.estado != EstadoAsientoContable.BORRADOR:
            raise ConflictError("Solo se puede modificar un asiento en estado BORRADOR.")

    @staticmethod
    @transaction.atomic
    def seed_plan_base(*, empresa, usuario=None):
        """Crea el plan minimo recomendado para iniciar la operacion contable."""
        creadas = []
        for _alias, (codigo, nombre, tipo) in ContabilidadService.CODIGOS_BASE.items():
            cuenta, created = PlanCuenta.all_objects.get_or_create(
                empresa=empresa,
                codigo=codigo,
                defaults={
                    "creado_por": usuario,
                    "nombre": nombre,
                    "tipo": tipo,
                    "acepta_movimientos": True,
                    "activa": True,
                },
            )
            if created:
                creadas.append(cuenta)
        return creadas

    @staticmethod
    @transaction.atomic
    def crear_asiento(
        *,
        empresa,
        fecha,
        glosa,
        movimientos_data,
        usuario=None,
        referencia_tipo="",
        referencia_id=None,
        origen=OrigenAsientoContable.MANUAL,
    ):
        """Crea un asiento contable con sus lineas y recalcula su cuadratura."""
        if not movimientos_data:
            raise BusinessRuleError("El asiento debe tener al menos una linea contable.")

        numero = SecuenciaService.obtener_siguiente_numero(empresa, TipoDocumento.ASIENTO_CONTABLE)
        asiento = AsientoContable.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=numero,
            fecha=fecha,
            glosa=glosa,
            referencia_tipo=referencia_tipo or "",
            referencia_id=referencia_id,
            origen=origen,
        )

        for movimiento in movimientos_data:
            cuenta = movimiento["cuenta"]
            MovimientoContable.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                asiento=asiento,
                cuenta=cuenta,
                glosa=movimiento.get("glosa") or glosa,
                debe=ContabilidadService._decimal(movimiento.get("debe")),
                haber=ContabilidadService._decimal(movimiento.get("haber")),
            )

        ContabilidadService.recalcular_totales(asiento=asiento)
        return asiento

    @staticmethod
    @transaction.atomic
    def contabilizar_asiento(*, asiento_id, empresa, usuario=None):
        """Contabiliza un asiento cuadrado y publica sus eventos de integracion."""
        asiento = AsientoContable.all_objects.select_for_update().filter(id=asiento_id, empresa=empresa).first()
        if not asiento:
            raise ResourceNotFoundError("Asiento contable no encontrado.")

        ContabilidadService.validar_editable(asiento=asiento)
        ContabilidadService.recalcular_totales(asiento=asiento)
        if not asiento.cuadrado:
            raise BusinessRuleError("No se puede contabilizar un asiento descuadrado.")

        asiento.estado = EstadoAsientoContable.CONTABILIZADO
        asiento.save(update_fields=["estado", "actualizado_en"])

        dedup_key = f"asiento:{asiento.id}:contabilizado"
        payload = {
            "asiento_id": str(asiento.id),
            "numero": asiento.numero,
            "fecha": str(asiento.fecha),
            "total_debe": str(asiento.total_debe),
            "total_haber": str(asiento.total_haber),
        }
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="AsientoContable",
            aggregate_id=asiento.id,
            event_type="contabilidad.asiento_contabilizado",
            payload=payload,
            meta={"source": "ContabilidadService"},
            idempotency_key=dedup_key,
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="contabilidad.asiento",
            event_name="asiento.contabilizado",
            payload=payload,
            usuario=usuario,
            dedup_key=dedup_key,
        )
        return asiento

    @staticmethod
    @transaction.atomic
    def anular_asiento(*, asiento_id, empresa, usuario=None):
        """Anula un asiento contabilizado preservando su trazabilidad historica."""
        asiento = AsientoContable.all_objects.select_for_update().filter(id=asiento_id, empresa=empresa).first()
        if not asiento:
            raise ResourceNotFoundError("Asiento contable no encontrado.")
        if asiento.estado == EstadoAsientoContable.ANULADO:
            return asiento
        if asiento.estado != EstadoAsientoContable.CONTABILIZADO:
            raise ConflictError("Solo se pueden anular asientos ya contabilizados.")

        asiento.estado = EstadoAsientoContable.ANULADO
        asiento.save(update_fields=["estado", "actualizado_en"])
        return asiento

    @staticmethod
    def _buscar_cuenta_por_codigo(*, empresa, codigo):
        cuenta = PlanCuenta.all_objects.filter(empresa=empresa, codigo=str(codigo).strip().upper(), activa=True).first()
        if not cuenta:
            raise BusinessRuleError(
                f"No existe la cuenta contable {codigo} para la empresa activa.",
                error_code="ACCOUNTING_ACCOUNT_MISSING",
            )
        return cuenta

    @staticmethod
    def _marcar_origen_contabilizado(*, aggregate_type, aggregate_id):
        """Actualiza el estado contable del documento origen cuando la centralizacion finaliza bien."""
        model_map = {
            "FacturaVenta": ("apps.ventas.models", "FacturaVenta"),
            "NotaCreditoVenta": ("apps.ventas.models", "NotaCreditoVenta"),
            "DocumentoCompraProveedor": ("apps.compras.models", "DocumentoCompraProveedor"),
            "MovimientoBancario": ("apps.core.models", "MovimientoBancario"),
        }
        mapping = model_map.get(aggregate_type)
        if not mapping:
            return

        module_name, model_name = mapping
        module = __import__(module_name, fromlist=[model_name])
        model = getattr(module, model_name)
        model.all_objects.filter(id=aggregate_id).update(
            estado_contable=EstadoContable.CONTABILIZADO,
        )

    @staticmethod
    @transaction.atomic
    def procesar_solicitudes_pendientes(*, empresa, usuario=None, limit=50):
        """Consume solicitudes del AccountingBridge y crea asientos contabilizados."""
        now = timezone.now()
        eventos = list(
            OutboxEvent.all_objects
            .select_for_update(skip_locked=True)
            .filter(
                empresa=empresa,
                topic="contabilidad",
                event_name="ASIENTO_SOLICITADO",
                status=OutboxStatus.PENDING,
                available_at__lte=now,
            )
            .order_by("available_at", "creado_en")[:limit]
        )

        procesados = []
        for event in eventos:
            event.status = OutboxStatus.PROCESSING
            event.attempts += 1
            event.save(update_fields=["status", "attempts"])

            try:
                entry = event.payload.get("entry") or {}
                movimientos = entry.get("movimientos") or []
                if not movimientos:
                    raise BusinessRuleError("La solicitud contable no contiene movimientos.")

                movimientos_data = []
                for linea in movimientos:
                    movimientos_data.append(
                        {
                            "cuenta": ContabilidadService._buscar_cuenta_por_codigo(
                                empresa=empresa,
                                codigo=linea.get("cuenta_codigo"),
                            ),
                            "glosa": linea.get("glosa") or entry.get("glosa") or "",
                            "debe": linea.get("debe", 0),
                            "haber": linea.get("haber", 0),
                        }
                    )

                asiento = ContabilidadService.crear_asiento(
                    empresa=empresa,
                    fecha=entry.get("fecha") or timezone.localdate(),
                    glosa=entry.get("glosa") or f"Asiento {event.payload.get('aggregate_type')}",
                    movimientos_data=movimientos_data,
                    usuario=usuario,
                    referencia_tipo=entry.get("referencia_tipo") or event.payload.get("aggregate_type") or "",
                    referencia_id=event.payload.get("aggregate_id"),
                    origen=OrigenAsientoContable.INTEGRACION,
                )
                ContabilidadService.contabilizar_asiento(
                    asiento_id=asiento.id,
                    empresa=empresa,
                    usuario=usuario,
                )
                ContabilidadService._marcar_origen_contabilizado(
                    aggregate_type=event.payload.get("aggregate_type"),
                    aggregate_id=event.payload.get("aggregate_id"),
                )
                asiento.refresh_from_db()
                OutboxService.mark_sent(event=event)
                procesados.append(asiento)
            except Exception as exc:  # pragma: no cover
                OutboxService.mark_failed(event=event, error_message=str(exc))

        return procesados
