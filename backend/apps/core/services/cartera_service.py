from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import BusinessRuleError
from apps.core.models import CuentaPorCobrar, CuentaPorPagar, EstadoCuenta, Moneda


class CarteraService:
    """Servicio base de CxC/CxP para integracion con ventas, compras y tesoreria."""

    @staticmethod
    def _estado_por_saldo(*, saldo, fecha_vencimiento, hoy):
        if saldo <= 0:
            return EstadoCuenta.PAGADA
        if fecha_vencimiento < hoy:
            return EstadoCuenta.VENCIDA
        return EstadoCuenta.PENDIENTE

    @staticmethod
    def _moneda_documento_o_base(*, empresa, moneda):
        if moneda:
            return moneda
        base = Moneda.all_objects.filter(empresa=empresa, es_base=True, activa=True).first()
        if not base:
            raise BusinessRuleError("La empresa no tiene moneda base activa para cartera.")
        return base

    @staticmethod
    @transaction.atomic
    def registrar_cxp_desde_documento_compra(*, documento, usuario=None):
        """Genera o actualiza CxP idempotente desde factura/guia de compra."""
        if Decimal(documento.total or 0) < 0:
            raise BusinessRuleError("El documento de compra no puede registrar monto negativo en CxP.")

        dias_credito = getattr(documento.proveedor, "dias_credito", 0) or 0
        fecha_vencimiento = documento.fecha_emision + timedelta(days=int(dias_credito))
        referencia = f"COMPRA-{documento.tipo_documento}-{documento.folio}"
        moneda = CarteraService._moneda_documento_o_base(
            empresa=documento.empresa,
            moneda=getattr(documento, "moneda", None),
        )

        cuenta, _ = CuentaPorPagar.all_objects.update_or_create(
            empresa=documento.empresa,
            documento_compra=documento,
            defaults={
                "proveedor": documento.proveedor,
                "moneda": moneda,
                "referencia": referencia,
                "fecha_emision": documento.fecha_emision,
                "fecha_vencimiento": fecha_vencimiento,
                "monto_total": documento.total,
                "saldo": documento.total,
                "estado": EstadoCuenta.PENDIENTE,
                "creado_por": usuario,
            },
        )
        return cuenta

    @staticmethod
    @transaction.atomic
    def registrar_cxc_manual(*, empresa, cliente, referencia, fecha_emision, fecha_vencimiento, monto_total, moneda=None, usuario=None):
        """Registra una CxC base para futura emision de ventas/facturacion."""
        monto_total = Decimal(str(monto_total or 0))
        if monto_total <= 0:
            raise BusinessRuleError("El monto total de CxC debe ser mayor a cero.")

        moneda = CarteraService._moneda_documento_o_base(empresa=empresa, moneda=moneda)

        return CuentaPorCobrar.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            cliente=cliente,
            moneda=moneda,
            referencia=referencia,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            monto_total=monto_total,
            saldo=monto_total,
            estado=EstadoCuenta.PENDIENTE,
        )

    @staticmethod
    @transaction.atomic
    def aplicar_pago_cuenta(*, cuenta, monto, fecha_pago):
        """Aplica pago parcial/total sobre una cuenta y recalcula estado."""
        monto = Decimal(str(monto or 0))
        if monto <= 0:
            raise BusinessRuleError("El monto de pago debe ser mayor a cero.")
        if monto > Decimal(cuenta.saldo or 0):
            raise BusinessRuleError("El pago excede el saldo pendiente de la cuenta.")

        nuevo_saldo = (Decimal(cuenta.saldo or 0) - monto).quantize(Decimal("0.01"))

        if nuevo_saldo == 0:
            estado = EstadoCuenta.PAGADA
        else:
            estado = EstadoCuenta.PARCIAL
            if cuenta.fecha_vencimiento < fecha_pago:
                estado = EstadoCuenta.VENCIDA

        cuenta.saldo = nuevo_saldo
        cuenta.estado = estado
        cuenta.save(update_fields=["saldo", "estado"])
        return cuenta
