from decimal import Decimal

import pytest

from apps.core.exceptions import BusinessRuleError
from apps.core.tenant import set_current_empresa
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import Bodega, InventorySnapshot, ReservaStock, StockLote, StockSerie
from apps.inventario.models.movimiento import TipoMovimiento
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Producto


@pytest.fixture
def producto_inventariable(db, empresa):
    set_current_empresa(empresa)
    return Producto.objects.create(
        nombre="Producto Inventariable",
        sku="INV-001",
        stock_actual=Decimal("0.00"),
        maneja_inventario=True,
        precio_referencia=Decimal("12000"),
    )


@pytest.mark.django_db
class TestInventarioService:
    def test_crea_bodega_principal_si_no_se_envia_bodega(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        mov = InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("3.00"),
            referencia="AJUSTE-1",
            empresa=empresa,
            usuario=usuario,
        )

        assert Bodega.all_objects.filter(empresa=empresa, nombre="Principal").exists()
        assert mov.bodega.nombre == "Principal"

    def test_tipo_movimiento_invalido_lanza_error(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        with pytest.raises(BusinessRuleError):
            InventarioService.registrar_movimiento(
                producto_id=producto_inventariable.id,
                tipo="TRANSFERENCIA",
                cantidad=Decimal("1.00"),
                referencia="INVALID-1",
                empresa=empresa,
                usuario=usuario,
            )

    def test_entrada_con_costo_unitario_recalcula_costo_ponderado(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)
        producto_inventariable.stock_actual = Decimal("10.00")
        producto_inventariable.costo_promedio = Decimal("100.0000")
        producto_inventariable.save(skip_clean=True, update_fields=["stock_actual", "costo_promedio"])

        mov = InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("10.00"),
            costo_unitario=Decimal("200.00"),
            referencia="COMPRA-001",
            empresa=empresa,
            usuario=usuario,
        )

        producto_inventariable.refresh_from_db()
        assert mov.costo_unitario == Decimal("200.0000")
        assert producto_inventariable.costo_promedio == Decimal("150.0000")

    def test_cada_movimiento_genera_snapshot_historico(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        mov = InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("4.00"),
            referencia="AJUSTE-2",
            empresa=empresa,
            usuario=usuario,
        )

        snapshot = InventorySnapshot.all_objects.get(movimiento=mov)
        assert snapshot.stock == Decimal("4.00")
        assert snapshot.valor_stock == Decimal("0.00")

    def test_no_permite_costo_unitario_negativo(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        with pytest.raises(BusinessRuleError):
            InventarioService.registrar_movimiento(
                producto_id=producto_inventariable.id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=Decimal("1.00"),
                costo_unitario=Decimal("-10.00"),
                referencia="COMPRA-NEG",
                empresa=empresa,
                usuario=usuario,
            )

    def test_salida_respeta_reservas_de_otros_documentos(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("5.00"),
            referencia="ENTRADA-RESERVA-1",
            empresa=empresa,
            usuario=usuario,
        )

        InventarioService.reservar_stock(
            producto_id=producto_inventariable.id,
            cantidad=Decimal("4.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="11111111-1111-1111-1111-111111111111",
            empresa=empresa,
            usuario=usuario,
        )

        with pytest.raises(BusinessRuleError):
            InventarioService.registrar_movimiento(
                producto_id=producto_inventariable.id,
                tipo=TipoMovimiento.SALIDA,
                cantidad=Decimal("2.00"),
                referencia="SALIDA-SIN-RESERVA",
                documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
                documento_id="22222222-2222-2222-2222-222222222222",
                empresa=empresa,
                usuario=usuario,
            )

    def test_salida_con_mismo_documento_consumiendo_reserva(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("5.00"),
            referencia="ENTRADA-RESERVA-2",
            empresa=empresa,
            usuario=usuario,
        )

        documento_id = "33333333-3333-3333-3333-333333333333"
        InventarioService.reservar_stock(
            producto_id=producto_inventariable.id,
            cantidad=Decimal("4.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id=documento_id,
            empresa=empresa,
            usuario=usuario,
        )

        InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.SALIDA,
            cantidad=Decimal("3.00"),
            referencia="SALIDA-CONSUME-RESERVA",
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id=documento_id,
            empresa=empresa,
            usuario=usuario,
        )

        pendiente = ReservaStock.all_objects.filter(
            empresa=empresa,
            producto=producto_inventariable,
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id=documento_id,
        ).first()
        assert pendiente is not None
        assert Decimal(pendiente.cantidad) == Decimal("1.00")

    def test_movimiento_rechaza_fracciones_si_producto_no_las_permite(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            nombre="Producto Sin Fracciones",
            sku="NO-FRAC-01",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            permite_decimales=False,
            precio_referencia=Decimal("9000"),
        )

        with pytest.raises(BusinessRuleError) as excinfo:
            InventarioService.registrar_movimiento(
                producto_id=producto.id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=Decimal("1.50"),
                referencia="FRACCION-INVALIDA",
                empresa=empresa,
                usuario=usuario,
            )

        assert "no permite cantidad de movimiento fraccionada" in str(excinfo.value)

    def test_trazabilidad_lote_actualiza_stock_lote(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Lote",
            sku="LOT-001",
            maneja_inventario=True,
            usa_lotes=True,
            precio_referencia=Decimal("1000"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("5"),
            referencia="ENTRADA-LOTE",
            empresa=empresa,
            usuario=usuario,
            lote_codigo="L-2026-01",
        )

        lote = StockLote.all_objects.get(empresa=empresa, producto=producto, lote_codigo="L-2026-01")
        assert Decimal(lote.stock) == Decimal("5")

    def test_trazabilidad_series_requiere_series_completas(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Serie",
            sku="SER-001",
            maneja_inventario=True,
            usa_lotes=True,
            usa_series=True,
            permite_decimales=False,
            precio_referencia=Decimal("2000"),
        )

        with pytest.raises(BusinessRuleError):
            InventarioService.registrar_movimiento(
                producto_id=producto.id,
                tipo=TipoMovimiento.ENTRADA,
                cantidad=Decimal("2"),
                referencia="ENTRADA-SERIE-INVALIDA",
                empresa=empresa,
                usuario=usuario,
                lote_codigo="L-SER-001",
                series=["S1"],
            )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("2"),
            referencia="ENTRADA-SERIE",
            empresa=empresa,
            usuario=usuario,
            lote_codigo="L-SER-001",
            series=["S1", "S2"],
        )

        assert StockSerie.all_objects.filter(empresa=empresa, producto=producto, estado="DISPONIBLE").count() == 2

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo=TipoMovimiento.SALIDA,
            cantidad=Decimal("1"),
            referencia="SALIDA-SERIE",
            empresa=empresa,
            usuario=usuario,
            lote_codigo="L-SER-001",
            series=["S1"],
        )

        assert StockSerie.all_objects.filter(
            empresa=empresa,
            producto=producto,
            serie_codigo="S1",
            estado="SALIDA",
        ).exists()

