from datetime import date
from decimal import Decimal

import pytest

from apps.auditoria.models import AuditEvent
from apps.compras.models import DocumentoCompraProveedor, DocumentoCompraProveedorItem
from apps.contactos.models import Contacto, Proveedor
from apps.core.models import DomainEvent, OutboxEvent
from apps.core.tenant import set_current_empresa, set_current_user
from apps.productos.models import Producto, ProductoSnapshot
from apps.productos.services.producto_service import ProductoService


@pytest.fixture
def proveedor_producto(db, empresa, usuario):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Proveedor Servicio Producto",
        rut="10111222-5",
        email="proveedor_producto_service@test.com",
    )
    return Proveedor.objects.create(empresa=empresa, contacto=contacto)


@pytest.mark.django_db
class TestProductoService:
    def test_crear_producto_registra_eventos_y_auditoria(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)

        producto = ProductoService.crear_producto(
            empresa=empresa,
            usuario=usuario,
            data={
                "nombre": "Producto Servicio",
                "sku": "PROD-SERVICE-001",
                "tipo": "PRODUCTO",
                "precio_referencia": Decimal("1500"),
                "precio_costo": Decimal("1000"),
                "maneja_inventario": True,
                "stock_actual": Decimal("4"),
                "activo": True,
            },
        )

        assert producto.pk is not None
        assert producto.costo_promedio == Decimal("1000")
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_type="Producto",
            aggregate_id=producto.id,
            event_type="producto.creado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="productos.catalogo",
            event_name="producto.creado",
        ).exists()
        assert AuditEvent.all_objects.filter(
            empresa=empresa,
            entity_type="PRODUCTO",
            entity_id=str(producto.id),
            event_type="PRODUCTO_CREADO",
        ).exists()
        snapshot = ProductoSnapshot.all_objects.get(empresa=empresa, producto_id_ref=producto.id, version=1)
        assert snapshot.event_type == "producto.creado"
        assert snapshot.snapshot["sku"] == "PROD-SERVICE-001"

    def test_actualizar_producto_registra_changed_fields(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Original",
            sku="PROD-UPD-001",
            precio_referencia=Decimal("2500"),
            precio_costo=Decimal("1800"),
            activo=True,
        )

        actualizado = ProductoService.actualizar_producto(
            producto_id=producto.id,
            empresa=empresa,
            usuario=usuario,
            data={
                "nombre": "Producto Actualizado",
                "precio_referencia": Decimal("3200"),
            },
        )

        assert actualizado.nombre == "PRODUCTO ACTUALIZADO"
        event = DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_type="Producto",
            aggregate_id=producto.id,
            event_type="producto.actualizado",
        ).latest("occurred_at")
        assert sorted(event.payload["changed_fields"]) == ["nombre", "precio_referencia"]

        audit = AuditEvent.all_objects.filter(
            empresa=empresa,
            entity_id=str(producto.id),
            event_type="PRODUCTO_ACTUALIZADO",
        ).latest("occurred_at")
        assert "nombre" in audit.changes
        assert "precio_referencia" in audit.changes
        snapshot = ProductoSnapshot.all_objects.get(empresa=empresa, producto_id_ref=producto.id, version=1)
        assert snapshot.event_type == "producto.actualizado"
        assert snapshot.changes["nombre"][1] == "PRODUCTO ACTUALIZADO"

    def test_eliminar_producto_con_historial_lo_anula_y_traza_eventos(self, empresa, usuario, proveedor_producto):
        set_current_empresa(empresa)
        set_current_user(usuario)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Con Historial Service",
            sku="PROD-DEL-001",
            precio_referencia=Decimal("2500"),
            activo=True,
        )

        documento = DocumentoCompraProveedor.objects.create(
            empresa=empresa,
            creado_por=usuario,
            tipo_documento="FACTURA_COMPRA",
            proveedor=proveedor_producto,
            folio="FAC-SERVICE-001",
            fecha_emision=date.today(),
            fecha_recepcion=date.today(),
            subtotal_neto=Decimal("7500"),
            impuestos=Decimal("0"),
            total=Decimal("7500"),
        )
        DocumentoCompraProveedorItem.objects.create(
            empresa=empresa,
            creado_por=usuario,
            documento=documento,
            producto=producto,
            cantidad=Decimal("3.00"),
            precio_unitario=Decimal("2500"),
            subtotal=Decimal("7500"),
        )

        result = ProductoService.eliminar_producto(
            producto_id=producto.id,
            empresa=empresa,
            usuario=usuario,
        )

        producto.refresh_from_db()
        assert result["deleted"] is False
        assert producto.activo is False
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_id=producto.id,
            event_type="producto.anulado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="productos.catalogo",
            event_name="producto.anulado",
        ).exists()
        assert AuditEvent.all_objects.filter(
            empresa=empresa,
            entity_id=str(producto.id),
            event_type="PRODUCTO_ANULADO",
        ).exists()
        snapshot = ProductoSnapshot.all_objects.filter(
            empresa=empresa,
            producto_id_ref=producto.id,
            event_type="producto.anulado",
        ).latest("version")
        assert snapshot.snapshot["activo"] == "False"
