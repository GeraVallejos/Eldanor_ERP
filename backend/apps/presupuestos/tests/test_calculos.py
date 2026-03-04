import pytest
from decimal import Decimal
from apps.presupuestos.services.calculo_service import CalculoService

class TestCalculoService:

    def test_calculo_item_simple(self):
        """Prueba un item sin impuestos ni descuentos."""
        res = CalculoService.calcular_totales_item(
            cantidad=Decimal("2"),
            precio_unitario=Decimal("100.00"),
            porcentaje_descuento=Decimal("0"),
            tasa_impuesto=Decimal("0")
        )
        assert res["subtotal"] == Decimal("200.00")
        assert res["total"] == Decimal("200.00")
        assert res["impuesto"] == Decimal("0.00")

    def test_calculo_item_con_iva(self):
        """Prueba un item con 19% de IVA (estándar en muchos países)."""
        res = CalculoService.calcular_totales_item(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            porcentaje_descuento=Decimal("0"),
            tasa_impuesto=Decimal("19.00")
        )
        # Subtotal: 100, Impuesto: 19, Total: 119
        assert res["subtotal"] == Decimal("100.00")
        assert res["impuesto"] == Decimal("19.00")
        assert res["total"] == Decimal("119.00")

    def test_redondeo_financiero(self):
        """
        Prueba que el redondeo sea 'HALF_UP'.
        Ejemplo: 10.555 debería ser 10.56
        """
        # 1 unidad a 10.555 con 0% IVA
        # Si el service redondea a 2 decimales:
        res = CalculoService.calcular_totales_item(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("10.555"),
            porcentaje_descuento=Decimal("0"),
            tasa_impuesto=Decimal("0")
        )
        assert res["subtotal"] == Decimal("10.56")

    def test_calculo_con_descuento(self):
        """Prueba item con 10% de descuento y luego 19% de IVA."""
        res = CalculoService.calcular_totales_item(
            cantidad=Decimal("1"),
            precio_unitario=Decimal("100.00"),
            porcentaje_descuento=Decimal("10.00"),
            tasa_impuesto=Decimal("19.00")
        )
        # 100 - 10% = 90 (Subtotal Neto)
        # 90 * 1.19 = 107.1 (Total)
        # Impuesto = 17.1
        assert res["subtotal"] == Decimal("90.00")
        assert res["descuento"] == Decimal("10.00")
        assert res["impuesto"] == Decimal("17.10")
        assert res["total"] == Decimal("107.10")