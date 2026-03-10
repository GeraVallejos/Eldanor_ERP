from decimal import Decimal

import pytest

from apps.core.exceptions import BusinessRuleError
from apps.core.tenant import set_current_empresa
from apps.inventario.models import Bodega, InventorySnapshot
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
