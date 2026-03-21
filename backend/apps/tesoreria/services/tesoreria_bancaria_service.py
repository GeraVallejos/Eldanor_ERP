from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.auditoria.models import AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError
from apps.core.services.accounting_bridge import AccountingBridge
from apps.core.services.domain_event_service import DomainEventService
from apps.core.services.outbox_service import OutboxService
from apps.documentos.models import EstadoContable
from apps.tesoreria.models import MovimientoBancario, OrigenMovimientoBancario
from apps.tesoreria.services.cartera_service import CarteraService


class TesoreriaBancariaService:
    """Gestiona movimientos bancarios y su conciliacion con cartera."""

    @staticmethod
    def _registrar_auditoria_movimiento(*, movimiento, usuario, action_code, event_type, summary, changes=None, payload=None, severity=AuditSeverity.INFO):
        """Registra auditoria funcional para operaciones sensibles de tesoreria bancaria."""
        AuditoriaService.registrar_evento(
            empresa=movimiento.empresa,
            usuario=usuario,
            module_code="TESORERIA",
            action_code=action_code,
            event_type=event_type,
            entity_type="MOVIMIENTO_BANCARIO",
            entity_id=str(movimiento.id),
            summary=summary,
            severity=severity,
            changes=changes or {},
            payload=payload or {},
            source="TesoreriaBancariaService",
            idempotency_key=f"audit:tesoreria-movimiento:{movimiento.id}:{event_type}",
        )

    @staticmethod
    @transaction.atomic
    def registrar_movimiento_manual(
        *,
        cuenta_bancaria,
        fecha,
        referencia,
        descripcion,
        tipo,
        monto,
        usuario=None,
    ):
        """Registra un movimiento bancario manual y publica su evento operativo."""
        movimiento = MovimientoBancario.all_objects.create(
            empresa=cuenta_bancaria.empresa,
            creado_por=usuario,
            cuenta_bancaria=cuenta_bancaria,
            fecha=fecha,
            referencia=referencia,
            descripcion=descripcion,
            tipo=tipo,
            monto=Decimal(str(monto or 0)),
            origen=OrigenMovimientoBancario.MANUAL,
        )

        DomainEventService.record_event(
            empresa=movimiento.empresa,
            aggregate_type="MovimientoBancario",
            aggregate_id=movimiento.id,
            event_type="tesoreria.movimiento_bancario.registrado",
            payload={
                "movimiento_id": str(movimiento.id),
                "cuenta_bancaria_id": str(cuenta_bancaria.id),
                "tipo": movimiento.tipo,
                "monto": str(movimiento.monto),
            },
            meta={"source": "TesoreriaBancariaService"},
            idempotency_key=f"tesoreria-banco:{movimiento.id}:registrado",
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=movimiento.empresa,
            topic="tesoreria.banco",
            event_name="movimiento_bancario.registrado",
            payload={
                "movimiento_id": str(movimiento.id),
                "cuenta_bancaria_id": str(cuenta_bancaria.id),
                "tipo": movimiento.tipo,
                "monto": str(movimiento.monto),
            },
            usuario=usuario,
            dedup_key=f"tesoreria-banco:{movimiento.id}:registrado",
        )
        TesoreriaBancariaService._registrar_auditoria_movimiento(
            movimiento=movimiento,
            usuario=usuario,
            action_code="CONCILIAR",
            event_type="TESORERIA_MOVIMIENTO_REGISTRADO",
            summary=f"Movimiento bancario {movimiento.referencia or movimiento.id} registrado manualmente.",
            payload={
                "cuenta_bancaria_id": str(cuenta_bancaria.id),
                "tipo": movimiento.tipo,
                "monto": str(movimiento.monto),
            },
        )
        return movimiento

    @staticmethod
    @transaction.atomic
    def conciliar_movimiento(*, movimiento, cuenta_por_cobrar=None, cuenta_por_pagar=None, usuario=None):
        """Concilia un movimiento bancario y aplica el pago correspondiente en cartera."""
        if movimiento.conciliado:
            raise BusinessRuleError(
                "El movimiento bancario ya fue conciliado.",
                error_code="BANK_MOVEMENT_ALREADY_RECONCILED",
            )
        if bool(cuenta_por_cobrar) == bool(cuenta_por_pagar):
            raise BusinessRuleError(
                "Debe indicar una cuenta por cobrar o una cuenta por pagar para conciliar.",
                error_code="BANK_RECONCILIATION_TARGET_REQUIRED",
            )

        cuenta = cuenta_por_cobrar or cuenta_por_pagar
        if cuenta.empresa_id != movimiento.empresa_id:
            raise BusinessRuleError(
                "La cuenta a conciliar no pertenece a la empresa activa.",
                error_code="BANK_RECONCILIATION_TENANT_MISMATCH",
            )

        CarteraService.aplicar_pago_cuenta(
            cuenta=cuenta,
            monto=movimiento.monto,
            fecha_pago=movimiento.fecha,
        )
        if cuenta_por_cobrar:
            AccountingBridge.request_entry(
                empresa=movimiento.empresa,
                aggregate_type="MovimientoBancario",
                aggregate_id=movimiento.id,
                entry_payload={
                    "fecha": str(movimiento.fecha),
                    "glosa": f"Cobro conciliado {movimiento.referencia or movimiento.id}",
                    "referencia_tipo": "MOVIMIENTO_BANCARIO",
                    "movimientos": [
                        {"cuenta_clave": "BANCO", "debe": str(movimiento.monto), "haber": "0"},
                        {"cuenta_clave": "CLIENTES", "debe": "0", "haber": str(movimiento.monto)},
                    ],
                },
                usuario=usuario,
                dedup_key=f"bank-accounting:{movimiento.id}:cxc",
            )
        else:
            AccountingBridge.request_entry(
                empresa=movimiento.empresa,
                aggregate_type="MovimientoBancario",
                aggregate_id=movimiento.id,
                entry_payload={
                    "fecha": str(movimiento.fecha),
                    "glosa": f"Pago conciliado {movimiento.referencia or movimiento.id}",
                    "referencia_tipo": "MOVIMIENTO_BANCARIO",
                    "movimientos": [
                        {"cuenta_clave": "PROVEEDORES", "debe": str(movimiento.monto), "haber": "0"},
                        {"cuenta_clave": "BANCO", "debe": "0", "haber": str(movimiento.monto)},
                    ],
                },
                usuario=usuario,
                dedup_key=f"bank-accounting:{movimiento.id}:cxp",
            )
        movimiento.estado_contable = EstadoContable.PENDIENTE

        movimiento.conciliado = True
        movimiento.conciliado_en = timezone.now()
        movimiento.origen = OrigenMovimientoBancario.CONCILIACION
        movimiento.cuenta_por_cobrar = cuenta_por_cobrar
        movimiento.cuenta_por_pagar = cuenta_por_pagar
        movimiento.save(
            update_fields=[
                "conciliado",
                "conciliado_en",
                "origen",
                "estado_contable",
                "cuenta_por_cobrar",
                "cuenta_por_pagar",
                "actualizado_en",
            ]
        )

        DomainEventService.record_event(
            empresa=movimiento.empresa,
            aggregate_type="MovimientoBancario",
            aggregate_id=movimiento.id,
            event_type="tesoreria.movimiento_bancario.conciliado",
            payload={
                "movimiento_id": str(movimiento.id),
                "cuenta_id": str(cuenta.id),
                "cuenta_tipo": cuenta.__class__.__name__,
                "monto": str(movimiento.monto),
            },
            meta={"source": "TesoreriaBancariaService"},
            idempotency_key=f"tesoreria-banco:{movimiento.id}:conciliado",
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=movimiento.empresa,
            topic="tesoreria.banco",
            event_name="movimiento_bancario.conciliado",
            payload={
                "movimiento_id": str(movimiento.id),
                "cuenta_id": str(cuenta.id),
                "cuenta_tipo": cuenta.__class__.__name__,
                "monto": str(movimiento.monto),
            },
            usuario=usuario,
            dedup_key=f"tesoreria-banco:{movimiento.id}:conciliado",
        )
        TesoreriaBancariaService._registrar_auditoria_movimiento(
            movimiento=movimiento,
            usuario=usuario,
            action_code="CONCILIAR",
            event_type="TESORERIA_MOVIMIENTO_CONCILIADO",
            summary=f"Movimiento bancario {movimiento.referencia or movimiento.id} conciliado.",
            changes={"conciliado": [False, True]},
            payload={
                "cuenta_id": str(cuenta.id),
                "cuenta_tipo": cuenta.__class__.__name__,
                "monto": str(movimiento.monto),
            },
        )
        return movimiento

    @staticmethod
    @transaction.atomic
    def desconciliar_movimiento(*, movimiento, usuario=None):
        """Revierte la conciliacion bancaria y recompone el saldo de la cuenta asociada."""
        if not movimiento.conciliado:
            raise BusinessRuleError(
                "El movimiento bancario no esta conciliado.",
                error_code="BANK_MOVEMENT_NOT_RECONCILED",
            )

        cuenta = movimiento.cuenta_por_cobrar or movimiento.cuenta_por_pagar
        if not cuenta:
            raise BusinessRuleError(
                "El movimiento conciliado no tiene una cuenta asociada para revertir.",
                error_code="BANK_RECONCILIATION_ACCOUNT_MISSING",
            )

        CarteraService.revertir_pago_cuenta(
            cuenta=cuenta,
            monto=movimiento.monto,
            fecha_referencia=movimiento.fecha,
        )

        if movimiento.cuenta_por_cobrar_id:
            AccountingBridge.request_entry(
                empresa=movimiento.empresa,
                aggregate_type="MovimientoBancario",
                aggregate_id=movimiento.id,
                entry_payload={
                    "fecha": str(timezone.localdate()),
                    "glosa": f"Reversa cobro conciliado {movimiento.referencia or movimiento.id}",
                    "referencia_tipo": "MOVIMIENTO_BANCARIO_REVERSA",
                    "estado_contable_objetivo": EstadoContable.REVERSADO,
                    "movimientos": [
                        {"cuenta_clave": "CLIENTES", "debe": str(movimiento.monto), "haber": "0"},
                        {"cuenta_clave": "BANCO", "debe": "0", "haber": str(movimiento.monto)},
                    ],
                },
                usuario=usuario,
                dedup_key=f"bank-accounting:{movimiento.id}:cxc:reversa",
            )
        else:
            AccountingBridge.request_entry(
                empresa=movimiento.empresa,
                aggregate_type="MovimientoBancario",
                aggregate_id=movimiento.id,
                entry_payload={
                    "fecha": str(timezone.localdate()),
                    "glosa": f"Reversa pago conciliado {movimiento.referencia or movimiento.id}",
                    "referencia_tipo": "MOVIMIENTO_BANCARIO_REVERSA",
                    "estado_contable_objetivo": EstadoContable.REVERSADO,
                    "movimientos": [
                        {"cuenta_clave": "BANCO", "debe": str(movimiento.monto), "haber": "0"},
                        {"cuenta_clave": "PROVEEDORES", "debe": "0", "haber": str(movimiento.monto)},
                    ],
                },
                usuario=usuario,
                dedup_key=f"bank-accounting:{movimiento.id}:cxp:reversa",
            )

        movimiento.conciliado = False
        movimiento.conciliado_en = None
        movimiento.origen = OrigenMovimientoBancario.MANUAL
        movimiento.estado_contable = EstadoContable.PENDIENTE
        movimiento.cuenta_por_cobrar = None
        movimiento.cuenta_por_pagar = None
        movimiento.save(
            update_fields=[
                "conciliado",
                "conciliado_en",
                "origen",
                "estado_contable",
                "cuenta_por_cobrar",
                "cuenta_por_pagar",
                "actualizado_en",
            ]
        )

        DomainEventService.record_event(
            empresa=movimiento.empresa,
            aggregate_type="MovimientoBancario",
            aggregate_id=movimiento.id,
            event_type="tesoreria.movimiento_bancario.desconciliado",
            payload={
                "movimiento_id": str(movimiento.id),
                "monto": str(movimiento.monto),
                "cuenta_tipo_anterior": cuenta.__class__.__name__,
                "cuenta_id_anterior": str(cuenta.id),
            },
            meta={"source": "TesoreriaBancariaService"},
            idempotency_key=f"tesoreria-banco:{movimiento.id}:desconciliado",
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=movimiento.empresa,
            topic="tesoreria.banco",
            event_name="movimiento_bancario.desconciliado",
            payload={
                "movimiento_id": str(movimiento.id),
                "monto": str(movimiento.monto),
                "cuenta_tipo_anterior": cuenta.__class__.__name__,
                "cuenta_id_anterior": str(cuenta.id),
            },
            usuario=usuario,
            dedup_key=f"tesoreria-banco:{movimiento.id}:desconciliado",
        )
        TesoreriaBancariaService._registrar_auditoria_movimiento(
            movimiento=movimiento,
            usuario=usuario,
            action_code="CONCILIAR",
            event_type="TESORERIA_MOVIMIENTO_DESCONCILIADO",
            summary=f"Movimiento bancario {movimiento.referencia or movimiento.id} desconciliado.",
            changes={"conciliado": [True, False]},
            payload={
                "cuenta_tipo_anterior": cuenta.__class__.__name__,
                "cuenta_id_anterior": str(cuenta.id),
                "monto": str(movimiento.monto),
            },
            severity=AuditSeverity.WARNING,
        )
        return movimiento
