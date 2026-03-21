from datetime import date
from decimal import Decimal

from apps.core.exceptions import BusinessRuleError, ResourceNotFoundError
from apps.tesoreria.models import Moneda, TipoCambio


class TipoCambioService:
    """Servicio de conversion monetaria para modulos de negocio."""

    @staticmethod
    def _as_decimal(value):
        return Decimal(str(value or 0))

    @staticmethod
    def registrar_tipo_cambio(*, empresa, moneda_origen, moneda_destino, fecha, tasa, usuario=None, observacion=""):
        """Registra o actualiza tipo de cambio por fecha para la empresa."""
        if moneda_origen.id == moneda_destino.id:
            raise BusinessRuleError("La moneda origen y destino deben ser distintas.")

        if moneda_origen.empresa_id != empresa.id or moneda_destino.empresa_id != empresa.id:
            raise BusinessRuleError("Las monedas no pertenecen a la empresa activa.")

        tasa_decimal = TipoCambioService._as_decimal(tasa)
        if tasa_decimal <= 0:
            raise BusinessRuleError("La tasa debe ser mayor a cero.")

        tipo_cambio, _ = TipoCambio.all_objects.update_or_create(
            empresa=empresa,
            moneda_origen=moneda_origen,
            moneda_destino=moneda_destino,
            fecha=fecha,
            defaults={
                "tasa": tasa_decimal,
                "observacion": str(observacion or "").strip(),
                "creado_por": usuario,
            },
        )
        return tipo_cambio

    @staticmethod
    def _resolver_moneda(*, empresa, moneda):
        if isinstance(moneda, Moneda):
            if moneda.empresa_id != empresa.id:
                raise BusinessRuleError("La moneda no pertenece a la empresa.")
            return moneda

        codigo = str(moneda or "").strip().upper()
        obj = Moneda.all_objects.filter(empresa=empresa, codigo=codigo).first()
        if not obj:
            raise ResourceNotFoundError(f"Moneda '{codigo}' no encontrada.")
        return obj

    @staticmethod
    def obtener_tasa(*, empresa, moneda_origen, moneda_destino, fecha=None):
        """Obtiene tasa vigente para la fecha, con fallback inverso y moneda base."""
        fecha = fecha or date.today()
        origen = TipoCambioService._resolver_moneda(empresa=empresa, moneda=moneda_origen)
        destino = TipoCambioService._resolver_moneda(empresa=empresa, moneda=moneda_destino)

        if origen.id == destino.id:
            return Decimal("1")

        directa = (
            TipoCambio.all_objects.filter(
                empresa=empresa,
                moneda_origen=origen,
                moneda_destino=destino,
                fecha__lte=fecha,
            )
            .order_by("-fecha", "-creado_en")
            .first()
        )
        if directa:
            return Decimal(directa.tasa)

        inversa = (
            TipoCambio.all_objects.filter(
                empresa=empresa,
                moneda_origen=destino,
                moneda_destino=origen,
                fecha__lte=fecha,
            )
            .order_by("-fecha", "-creado_en")
            .first()
        )
        if inversa:
            return (Decimal("1") / Decimal(inversa.tasa)).quantize(Decimal("0.0000001"))

        raise ResourceNotFoundError(
            f"No existe tipo de cambio para {origen.codigo}->{destino.codigo} en fecha {fecha}."
        )

    @staticmethod
    def convertir_monto(*, empresa, monto, moneda_origen, moneda_destino, fecha=None, decimales=2):
        """Convierte un monto entre monedas respetando tasa vigente."""
        tasa = TipoCambioService.obtener_tasa(
            empresa=empresa,
            moneda_origen=moneda_origen,
            moneda_destino=moneda_destino,
            fecha=fecha,
        )
        cuantizador = Decimal("1").scaleb(-int(decimales))
        return (TipoCambioService._as_decimal(monto) * tasa).quantize(cuantizador)
