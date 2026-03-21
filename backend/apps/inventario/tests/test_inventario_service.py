from decimal import Decimal

import pytest

from apps.core.exceptions import BusinessRuleError
from apps.core.tenant import set_current_empresa
from apps.documentos.models import TipoDocumentoReferencia
from apps.inventario.models import Bodega, InventorySnapshot, ReservaStock, StockLote, StockProducto, StockSerie
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

    def test_regularizar_stock_objetivo_crea_ajuste_desde_diferencia(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("10.00"),
            referencia="ENTRADA-BASE-REG",
            empresa=empresa,
            usuario=usuario,
        )

        movimiento = InventarioService.regularizar_stock(
            producto_id=producto_inventariable.id,
            stock_objetivo=Decimal("6.00"),
            referencia="AJUSTE-CONTEO",
            empresa=empresa,
            usuario=usuario,
        )

        producto_inventariable.refresh_from_db()
        assert movimiento.tipo == TipoMovimiento.SALIDA
        assert movimiento.documento_tipo == TipoDocumentoReferencia.AJUSTE
        assert Decimal(movimiento.cantidad) == Decimal("4.00")
        assert producto_inventariable.stock_actual == Decimal("6.00")

    def test_regularizar_rechaza_stock_objetivo_bajo_reservado(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("5.00"),
            referencia="ENTRADA-RESERVA-REG",
            empresa=empresa,
            usuario=usuario,
        )
        InventarioService.reservar_stock(
            producto_id=producto_inventariable.id,
            cantidad=Decimal("3.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="55555555-5555-5555-5555-555555555555",
            empresa=empresa,
            usuario=usuario,
        )

        with pytest.raises(BusinessRuleError) as excinfo:
            InventarioService.regularizar_stock(
                producto_id=producto_inventariable.id,
                stock_objetivo=Decimal("2.00"),
                referencia="AJUSTE-INVALIDO",
                empresa=empresa,
                usuario=usuario,
            )

        assert "reservado" in str(excinfo.value).lower()

    def test_previsualizar_regularizacion_informa_diferencia_y_reservas(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)

        movimiento = InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("9.00"),
            referencia="ENTRADA-PREVIA",
            empresa=empresa,
            usuario=usuario,
        )
        InventarioService.reservar_stock(
            producto_id=producto_inventariable.id,
            bodega_id=movimiento.bodega_id,
            cantidad=Decimal("2.00"),
            documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
            documento_id="77777777-7777-7777-7777-777777777777",
            empresa=empresa,
            usuario=usuario,
        )

        preview = InventarioService.previsualizar_regularizacion_stock(
            producto_id=producto_inventariable.id,
            bodega_id=movimiento.bodega_id,
            stock_objetivo=Decimal("6.00"),
            empresa=empresa,
        )

        assert preview["tipo_movimiento"] == TipoMovimiento.SALIDA
        assert Decimal(preview["diferencia"]) == Decimal("-3.00")
        assert Decimal(preview["reservado_total"]) == Decimal("2.00")
        assert preview["ajustable"] is True

    def test_trazabilidad_series_marca_salida(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Serie Salida",
            sku="SER-OUT-001",
            maneja_inventario=True,
            usa_lotes=True,
            usa_series=True,
            permite_decimales=False,
            precio_referencia=Decimal("2000"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("2"),
            referencia="ENTRADA-SERIE-SALIDA",
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

    def test_trasladar_stock_mueve_existencia_entre_bodegas(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)
        bodega_origen = Bodega.all_objects.create(empresa=empresa, creado_por=usuario, nombre="Origen")
        bodega_destino = Bodega.all_objects.create(empresa=empresa, creado_por=usuario, nombre="Destino")

        InventarioService.registrar_movimiento(
            producto_id=producto_inventariable.id,
            bodega_id=bodega_origen.id,
            tipo=TipoMovimiento.ENTRADA,
            cantidad=Decimal("7.00"),
            referencia="ENTRADA-ORIGEN",
            empresa=empresa,
            usuario=usuario,
        )

        traslado = InventarioService.trasladar_stock(
            producto_id=producto_inventariable.id,
            bodega_origen_id=bodega_origen.id,
            bodega_destino_id=bodega_destino.id,
            cantidad=Decimal("3.00"),
            referencia="TRASLADO-TEST",
            empresa=empresa,
            usuario=usuario,
        )

        stock_origen = StockProducto.all_objects.get(
            empresa=empresa,
            producto=producto_inventariable,
            bodega=bodega_origen,
        )
        stock_destino = StockProducto.all_objects.get(
            empresa=empresa,
            producto=producto_inventariable,
            bodega=bodega_destino,
        )
        producto_inventariable.refresh_from_db()
        assert traslado["movimiento_salida"].documento_tipo == TipoDocumentoReferencia.TRASLADO
        assert traslado["movimiento_entrada"].documento_tipo == TipoDocumentoReferencia.TRASLADO
        assert traslado["movimiento_salida"].stock_nuevo == Decimal("4.00")
        assert traslado["movimiento_entrada"].stock_nuevo == Decimal("3.00")
        assert producto_inventariable.stock_actual == Decimal("7.00")
        assert Decimal(stock_origen.stock) == Decimal("4.00")
        assert Decimal(stock_destino.stock) == Decimal("3.00")

    def test_trasladar_stock_rechaza_misma_bodega(self, empresa, usuario, producto_inventariable):
        set_current_empresa(empresa)
        bodega = Bodega.all_objects.create(empresa=empresa, creado_por=usuario, nombre="Unica")

        with pytest.raises(BusinessRuleError) as excinfo:
            InventarioService.trasladar_stock(
                producto_id=producto_inventariable.id,
                bodega_origen_id=bodega.id,
                bodega_destino_id=bodega.id,
                cantidad=Decimal("1.00"),
                referencia="TRASLADO-INVALIDO",
                empresa=empresa,
                usuario=usuario,
            )

        assert "distintas" in str(excinfo.value)

