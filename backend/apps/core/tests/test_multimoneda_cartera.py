from datetime import date
from decimal import Decimal

import pytest

from apps.contactos.models import Contacto, Cliente
from apps.core.services import CarteraService, TipoCambioService
from apps.core.models import CuentaPorCobrar, Moneda


@pytest.mark.django_db
class TestMultimonedaCartera:
    def test_convertir_monto_con_tasa_directa(self, empresa, usuario):
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        usd = Moneda.all_objects.get(empresa=empresa, codigo="USD")

        TipoCambioService.registrar_tipo_cambio(
            empresa=empresa,
            moneda_origen=usd,
            moneda_destino=clp,
            fecha=date(2026, 3, 1),
            tasa=Decimal("950"),
            usuario=usuario,
        )

        monto = TipoCambioService.convertir_monto(
            empresa=empresa,
            monto=Decimal("10"),
            moneda_origen=usd,
            moneda_destino=clp,
            fecha=date(2026, 3, 2),
        )

        assert monto == Decimal("9500.00")

    def test_convertir_monto_con_tasa_inversa(self, empresa, usuario):
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        usd = Moneda.all_objects.get(empresa=empresa, codigo="USD")

        TipoCambioService.registrar_tipo_cambio(
            empresa=empresa,
            moneda_origen=usd,
            moneda_destino=clp,
            fecha=date(2026, 3, 1),
            tasa=Decimal("1000"),
            usuario=usuario,
        )

        monto = TipoCambioService.convertir_monto(
            empresa=empresa,
            monto=Decimal("1000"),
            moneda_origen=clp,
            moneda_destino=usd,
            fecha=date(2026, 3, 2),
            decimales=4,
        )

        assert monto == Decimal("1.0000")

    def test_registrar_cxc_manual(self, empresa, usuario):
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente CxC",
            rut="11122333-5",
            email="cliente_cxc@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        cuenta = CarteraService.registrar_cxc_manual(
            empresa=empresa,
            cliente=cliente,
            referencia="CXC-0001",
            fecha_emision=date(2026, 3, 10),
            fecha_vencimiento=date(2026, 3, 25),
            monto_total=Decimal("150000"),
            moneda=clp,
            usuario=usuario,
        )

        assert cuenta.saldo == Decimal("150000")
        assert CuentaPorCobrar.all_objects.filter(empresa=empresa, referencia="CXC-0001").exists()


