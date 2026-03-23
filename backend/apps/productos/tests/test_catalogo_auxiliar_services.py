from datetime import date
from decimal import Decimal

import pytest

from apps.auditoria.models import AuditEvent
from apps.core.exceptions import ConflictError
from apps.core.models import DomainEvent, OutboxEvent
from apps.core.tenant import set_current_empresa, set_current_user
from apps.productos.models import Categoria, Producto
from apps.productos.services.catalogo_service import CategoriaService, ImpuestoService
from apps.productos.services.lista_precio_service import ListaPrecioItemService, ListaPrecioService
from apps.tesoreria.models import Moneda


@pytest.mark.django_db
class TestCatalogoAuxiliarServices:
    def test_categoria_service_desactiva_si_tiene_productos(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)

        categoria = Categoria.objects.create(empresa=empresa, creado_por=usuario, nombre="Ferreteria")
        Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Martillo servicio catalogo",
            sku="CAT-SVC-001",
            categoria=categoria,
            precio_referencia=Decimal("1000"),
        )

        result = CategoriaService.eliminar_categoria(
            categoria_id=categoria.id,
            empresa=empresa,
            usuario=usuario,
        )

        categoria.refresh_from_db()
        assert result["deleted"] is False
        assert categoria.activa is False
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_type="CategoriaProducto",
            aggregate_id=categoria.id,
            event_type="categoria_producto.desactivada",
        ).exists()

    def test_impuesto_service_registra_eventos(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)

        impuesto = ImpuestoService.crear_impuesto(
            empresa=empresa,
            usuario=usuario,
            data={"nombre": "IVA Reducido", "porcentaje": Decimal("10"), "activo": True},
        )

        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_type="ImpuestoProducto",
            aggregate_id=impuesto.id,
            event_type="impuesto_producto.creado",
        ).exists()
        assert OutboxEvent.all_objects.filter(
            empresa=empresa,
            topic="productos.catalogo",
            event_name="impuesto_producto.creado",
        ).exists()
        assert AuditEvent.all_objects.filter(
            empresa=empresa,
            entity_type="IMPUESTO_PRODUCTO",
            entity_id=str(impuesto.id),
            event_type="IMPUESTO_PRODUCTO_CREADO",
        ).exists()

    def test_lista_precio_item_service_registra_cambios(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Lista Servicio",
            sku="LISTA-SVC-001",
            precio_referencia=Decimal("1500"),
        )
        lista = ListaPrecioService.crear_lista(
            empresa=empresa,
            usuario=usuario,
            data={
                "nombre": "Lista Mayorista",
                "moneda": moneda,
                "cliente": None,
                "fecha_desde": date(2026, 1, 1),
                "fecha_hasta": date(2026, 12, 31),
                "activa": True,
                "prioridad": 15,
            },
        )

        item = ListaPrecioItemService.crear_item(
            empresa=empresa,
            usuario=usuario,
            data={
                "lista": lista,
                "producto": producto,
                "precio": Decimal("1400"),
                "descuento_maximo": Decimal("7.5"),
            },
        )

        actualizado = ListaPrecioItemService.actualizar_item(
            item_id=item.id,
            empresa=empresa,
            usuario=usuario,
            data={"precio": Decimal("1350"), "descuento_maximo": Decimal("10")},
        )

        assert actualizado.precio == Decimal("1350")
        assert DomainEvent.all_objects.filter(
            empresa=empresa,
            aggregate_type="ListaPrecioItem",
            aggregate_id=item.id,
            event_type="lista_precio_item.actualizado",
        ).exists()

    def test_lista_precio_service_rechaza_solapamiento_activo_misma_prioridad(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        ListaPrecioService.crear_lista(
            empresa=empresa,
            usuario=usuario,
            data={
                "nombre": "Lista General Base",
                "moneda": moneda,
                "cliente": None,
                "fecha_desde": date(2026, 1, 1),
                "fecha_hasta": date(2026, 12, 31),
                "activa": True,
                "prioridad": 10,
            },
        )

        with pytest.raises(ConflictError) as exc:
            ListaPrecioService.crear_lista(
                empresa=empresa,
                usuario=usuario,
                data={
                    "nombre": "Lista General Duplicada",
                    "moneda": moneda,
                    "cliente": None,
                    "fecha_desde": date(2026, 6, 1),
                    "fecha_hasta": None,
                    "activa": True,
                    "prioridad": 10,
                },
            )

        assert exc.value.error_code == "CONFLICT"

    def test_lista_precio_service_rechaza_lista_futura_si_hay_vigencia_abierta(self, empresa, usuario):
        set_current_empresa(empresa)
        set_current_user(usuario)
        moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        ListaPrecioService.crear_lista(
            empresa=empresa,
            usuario=usuario,
            data={
                "nombre": "Lista Abierta",
                "moneda": moneda,
                "cliente": None,
                "fecha_desde": date(2026, 3, 1),
                "fecha_hasta": None,
                "activa": True,
                "prioridad": 20,
            },
        )

        with pytest.raises(ConflictError):
            ListaPrecioService.crear_lista(
                empresa=empresa,
                usuario=usuario,
                data={
                    "nombre": "Lista Futura Conflicto",
                    "moneda": moneda,
                    "cliente": None,
                    "fecha_desde": date(2027, 1, 1),
                    "fecha_hasta": date(2027, 12, 31),
                    "activa": True,
                    "prioridad": 20,
                },
            )
