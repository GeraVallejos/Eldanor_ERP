from datetime import date
from decimal import Decimal

import pytest

from apps.compras.models import DocumentoCompraProveedor, DocumentoCompraProveedorItem, EstadoDocumentoCompra
from apps.compras.services import DocumentoCompraService
from apps.contactos.models import Contacto, Proveedor
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import CuentaPorPagar, UserEmpresa
from apps.inventario.models import MovimientoInventario
from apps.inventario.models import StockProducto
from apps.inventario.services.inventario_service import InventarioService
from apps.productos.models import Producto


@pytest.fixture
def owner_usuario(db, empresa):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="owner_docs_compra",
        email="owner_docs_compra@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )
    UserEmpresa.objects.create(user=user, empresa=empresa, rol="OWNER", activo=True)
    return user


@pytest.fixture
def proveedor(db, empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Proveedor Documentos",
        rut="77888999-0",
        email="proveedor_docs@test.com",
    )
    return Proveedor.objects.create(empresa=empresa, contacto=contacto)


@pytest.fixture
def producto(db, empresa, owner_usuario):
    return Producto.objects.create(
        empresa=empresa,
        creado_por=owner_usuario,
        nombre="Producto Documento Compra",
        sku="PDC-001",
        stock_actual=Decimal("0.00"),
        maneja_inventario=True,
        precio_referencia=Decimal("2000"),
    )


@pytest.fixture
def guia_borrador(db, empresa, owner_usuario, proveedor):
    return DocumentoCompraProveedor.objects.create(
        empresa=empresa,
        creado_por=owner_usuario,
        tipo_documento="GUIA_RECEPCION",
        proveedor=proveedor,
        folio="GR-001",
        fecha_emision=date.today(),
        fecha_recepcion=date.today(),
        subtotal_neto=Decimal("10000"),
        total=Decimal("10000"),
    )


@pytest.mark.django_db
class TestDocumentoCompraService:

    def test_confirmar_guia_genera_movimiento_inventario(self, empresa, owner_usuario, guia_borrador, producto):
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=guia_borrador,
            producto=producto,
            cantidad=Decimal("5"),
            precio_unitario=Decimal("2000"),
            subtotal=Decimal("10000"),
        )

        doc = DocumentoCompraService.confirmar_guia(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        assert doc.estado == EstadoDocumentoCompra.CONFIRMADO
        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            producto=producto,
            documento_tipo="GUIA_RECEPCION",
            documento_id=guia_borrador.id,
        ).exists()
        movimiento = MovimientoInventario.all_objects.get(
            empresa=empresa,
            producto=producto,
            documento_tipo="GUIA_RECEPCION",
            documento_id=guia_borrador.id,
        )
        assert movimiento.referencia == "GUIA GR-001"

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("5")

    def test_confirmar_guia_sin_items_lanza_error(self, empresa, owner_usuario, guia_borrador):
        with pytest.raises(BusinessRuleError):
            DocumentoCompraService.confirmar_guia(
                documento_id=guia_borrador.id,
                empresa=empresa,
                usuario=owner_usuario,
            )

    def test_confirmar_guia_idempotente(self, empresa, owner_usuario, guia_borrador, producto):
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=guia_borrador,
            producto=producto,
            cantidad=Decimal("3"),
            precio_unitario=Decimal("2000"),
            subtotal=Decimal("6000"),
        )

        DocumentoCompraService.confirmar_guia(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )
        # Segunda llamada no debe crear movimientos adicionales ni lanzar error
        DocumentoCompraService.confirmar_guia(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            documento_tipo="GUIA_RECEPCION",
            documento_id=guia_borrador.id,
        ).count() == 1

    def test_anular_guia_confirmada_genera_movimiento_compensatorio(self, empresa, owner_usuario, guia_borrador, producto):
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=guia_borrador,
            producto=producto,
            cantidad=Decimal("4"),
            precio_unitario=Decimal("2000"),
            subtotal=Decimal("8000"),
        )

        DocumentoCompraService.confirmar_guia(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        producto.refresh_from_db()
        stock_tras_guia = producto.stock_actual

        DocumentoCompraService.anular_documento(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        guia_borrador.refresh_from_db()
        assert guia_borrador.estado == EstadoDocumentoCompra.ANULADO

        producto.refresh_from_db()
        assert producto.stock_actual == stock_tras_guia - Decimal("4")

    def test_confirmar_factura(self, empresa, owner_usuario, proveedor):
        factura = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor,
            folio="FAC-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("5000"),
            impuestos=Decimal("950"),
            total=Decimal("5950"),
        )

        producto_factura = Producto.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Producto Factura",
            sku="PF-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("5000"),
        )

        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=factura,
            producto=producto_factura,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("5000"),
            subtotal=Decimal("5000"),
        )

        doc = DocumentoCompraService.confirmar_factura(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        assert doc.estado == EstadoDocumentoCompra.CONFIRMADO
        # Sin guía ni recepción previa: la factura actúa como documento de entrada
        # (caso Chile: proveedor solo emite factura, sin guía de despacho).
        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            producto=producto_factura,
            documento_tipo="FACTURA_COMPRA",
            documento_id=factura.id,
        ).exists()
        producto_factura.refresh_from_db()
        assert producto_factura.stock_actual == Decimal("1")
        assert CuentaPorPagar.all_objects.filter(empresa=empresa, documento_compra=factura).exists()

    def test_anular_factura_confirmada_genera_movimiento_compensatorio(self, empresa, owner_usuario, proveedor):
        factura = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor,
            folio="FAC-ANU-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("7000"),
            impuestos=Decimal("1330"),
            total=Decimal("8330"),
        )

        producto_factura = Producto.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Producto Factura Anulable",
            sku="PFA-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("7000"),
        )

        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=factura,
            producto=producto_factura,
            cantidad=Decimal("2"),
            precio_unitario=Decimal("3500"),
            subtotal=Decimal("7000"),
        )

        DocumentoCompraService.confirmar_factura(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
        )
        DocumentoCompraService.anular_documento(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        factura.refresh_from_db()
        assert factura.estado == EstadoDocumentoCompra.ANULADO
        # Factura sin entrada física previa generó 1 movimiento de entrada al confirmar
        # y 1 movimiento compensatorio (salida) al anular → total 2 movimientos.
        assert MovimientoInventario.all_objects.filter(
            empresa=empresa,
            documento_tipo="FACTURA_COMPRA",
            documento_id=factura.id,
        ).count() == 2
        producto_factura.refresh_from_db()
        assert producto_factura.stock_actual == Decimal("0")

    def test_confirmar_guia_no_encontrada_lanza_error(self, empresa, owner_usuario):
        import uuid
        with pytest.raises(ResourceNotFoundError):
            DocumentoCompraService.confirmar_guia(
                documento_id=uuid.uuid4(),
                empresa=empresa,
                usuario=owner_usuario,
            )

    def test_anular_documento_borrador_sin_movimiento(self, empresa, owner_usuario, guia_borrador):
        doc = DocumentoCompraService.anular_documento(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        assert doc.estado == EstadoDocumentoCompra.ANULADO
        assert not MovimientoInventario.all_objects.filter(
            empresa=empresa,
            documento_tipo="GUIA_RECEPCION",
            documento_id=guia_borrador.id,
        ).exists()

    def test_corregir_documento_confirmado_anula_y_clona_en_borrador(self, empresa, owner_usuario, proveedor):
        factura = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor,
            folio="FAC-CORR-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("10000"),
            impuestos=Decimal("1900"),
            total=Decimal("11900"),
        )

        producto_factura = Producto.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Producto Correccion",
            sku="PCOR-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("10000"),
        )

        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=factura,
            producto=producto_factura,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("10000"),
            subtotal=Decimal("10000"),
        )

        DocumentoCompraService.confirmar_factura(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        corregido = DocumentoCompraService.corregir_documento(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
            motivo="Error en el valor unitario",
        )

        factura.refresh_from_db()
        assert factura.estado == EstadoDocumentoCompra.ANULADO
        assert corregido.estado == EstadoDocumentoCompra.BORRADOR
        assert corregido.documento_origen_id == factura.id
        assert corregido.motivo_correccion == "Error en el valor unitario"
        assert corregido.corregido_por_id == owner_usuario.id
        assert corregido.items.count() == 1

    def test_corregir_documento_exige_motivo(self, empresa, owner_usuario, guia_borrador, producto):
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=guia_borrador,
            producto=producto,
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            subtotal=Decimal("1000"),
        )
        DocumentoCompraService.confirmar_guia(
            documento_id=guia_borrador.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        with pytest.raises(BusinessRuleError):
            DocumentoCompraService.corregir_documento(
                documento_id=guia_borrador.id,
                empresa=empresa,
                usuario=owner_usuario,
                motivo="  ",
            )

    def test_anular_factura_revierte_valorizacion_resumen(self, empresa, owner_usuario, proveedor):
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            nombre="Producto Valorizacion",
            sku="PVAL-001",
            stock_actual=Decimal("0.00"),
            maneja_inventario=True,
            precio_referencia=Decimal("1000"),
        )

        InventarioService.registrar_movimiento(
            producto_id=producto.id,
            tipo="ENTRADA",
            cantidad=Decimal("10.00"),
            costo_unitario=Decimal("100.00"),
            referencia="BASE-VAL",
            empresa=empresa,
            usuario=owner_usuario,
        )
        producto.refresh_from_db()

        stock_base = StockProducto.all_objects.get(empresa=empresa, producto=producto)
        valor_base = stock_base.valor_stock
        costo_base = producto.costo_promedio

        factura = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor,
            folio="FAC-VAL-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("2000"),
            impuestos=Decimal("0"),
            total=Decimal("2000"),
        )
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=owner_usuario,
            documento=factura,
            producto=producto,
            cantidad=Decimal("10"),
            precio_unitario=Decimal("200"),
            subtotal=Decimal("2000"),
        )

        DocumentoCompraService.confirmar_factura(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
        )
        DocumentoCompraService.anular_documento(
            documento_id=factura.id,
            empresa=empresa,
            usuario=owner_usuario,
        )

        producto.refresh_from_db()
        stock_final = StockProducto.all_objects.get(empresa=empresa, producto=producto)

        assert producto.stock_actual == Decimal("10.00")
        assert stock_final.stock == Decimal("10.00")
        assert stock_final.valor_stock == valor_base
        assert producto.costo_promedio == costo_base
