from datetime import date
from decimal import Decimal

import pytest

from apps.contactos.models import Cliente, Contacto
from apps.tesoreria.models import Moneda
from apps.tesoreria.services import TipoCambioService
from apps.core.tenant import set_current_empresa
from apps.productos.models import ListaPrecio, ListaPrecioItem, Producto
from apps.productos.services.precio_service import PrecioComercialService


@pytest.mark.django_db
class TestPrecioComercialService:
    def test_resuelve_precio_desde_lista_cliente(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Lista",
            sku="LISTA-001",
            precio_referencia=Decimal("10000"),
        )
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Lista",
            rut="14141414-3",
            email="cliente_lista@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Lista Cliente",
            moneda=clp,
            cliente=cliente,
            fecha_desde=date(2026, 1, 1),
            prioridad=10,
            activa=True,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=usuario,
            lista=lista,
            producto=producto,
            precio=Decimal("8500"),
        )

        resultado = PrecioComercialService.obtener_precio(
            empresa=empresa,
            producto=producto,
            cliente=cliente,
            fecha=date(2026, 3, 12),
        )

        assert resultado["fuente"] == "LISTA_PRECIO"
        assert resultado["precio"] == Decimal("8500")

    def test_convierte_precio_lista_a_otra_moneda(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto USD",
            sku="LISTA-USD-001",
            precio_referencia=Decimal("10000"),
        )
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")
        usd = Moneda.all_objects.get(empresa=empresa, codigo="USD")

        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Lista General CLP",
            moneda=clp,
            fecha_desde=date(2026, 1, 1),
            prioridad=100,
            activa=True,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=usuario,
            lista=lista,
            producto=producto,
            precio=Decimal("9500"),
        )
        TipoCambioService.registrar_tipo_cambio(
            empresa=empresa,
            moneda_origen=clp,
            moneda_destino=usd,
            fecha=date(2026, 3, 1),
            tasa=Decimal("0.001"),
            usuario=usuario,
        )

        resultado = PrecioComercialService.obtener_precio(
            empresa=empresa,
            producto=producto,
            fecha=date(2026, 3, 12),
            moneda_destino=usd,
        )

        assert resultado["moneda"].codigo == "USD"
        assert resultado["precio"] == Decimal("9.50")

    def test_no_atribuye_lista_si_no_existe_item_para_el_producto(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Sin Item",
            sku="SIN-ITEM-001",
            precio_referencia=Decimal("12345"),
        )
        otro_producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto En Lista",
            sku="CON-ITEM-001",
            precio_referencia=Decimal("5000"),
        )
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Fallback",
            rut="15151515-0",
            email="cliente_fallback@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        lista = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Lista Cliente Fallback",
            moneda=clp,
            cliente=cliente,
            fecha_desde=date(2026, 1, 1),
            prioridad=10,
            activa=True,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=usuario,
            lista=lista,
            producto=otro_producto,
            precio=Decimal("4500"),
        )

        resultado = PrecioComercialService.obtener_precio(
            empresa=empresa,
            producto=producto,
            cliente=cliente,
            fecha=date(2026, 3, 12),
        )

        assert resultado["fuente"] == "PRODUCTO_REFERENCIA"
        assert resultado["precio"] == Decimal("12345")
        assert resultado["lista"] is None

    def test_fallback_a_lista_general_si_lista_cliente_no_tiene_item(self, empresa, usuario):
        set_current_empresa(empresa)
        producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Fallback General",
            sku="FALLBACK-GEN-001",
            precio_referencia=Decimal("12345"),
        )
        otro_producto = Producto.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Producto Solo Cliente",
            sku="SOLO-CLIENTE-001",
            precio_referencia=Decimal("5000"),
        )
        contacto = Contacto.objects.create(
            empresa=empresa,
            nombre="Cliente Jerarquia",
            rut="16161616-8",
            email="cliente_jerarquia@test.com",
        )
        cliente = Cliente.objects.create(empresa=empresa, contacto=contacto)
        clp = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

        lista_cliente = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Lista Cliente Jerarquia",
            moneda=clp,
            cliente=cliente,
            fecha_desde=date(2026, 1, 1),
            prioridad=10,
            activa=True,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=usuario,
            lista=lista_cliente,
            producto=otro_producto,
            precio=Decimal("4500"),
        )

        lista_general = ListaPrecio.objects.create(
            empresa=empresa,
            creado_por=usuario,
            nombre="Lista General Base",
            moneda=clp,
            fecha_desde=date(2026, 1, 1),
            prioridad=100,
            activa=True,
        )
        ListaPrecioItem.objects.create(
            empresa=empresa,
            creado_por=usuario,
            lista=lista_general,
            producto=producto,
            precio=Decimal("9900"),
        )

        resultado = PrecioComercialService.obtener_precio(
            empresa=empresa,
            producto=producto,
            cliente=cliente,
            fecha=date(2026, 3, 12),
        )

        assert resultado["fuente"] == "LISTA_PRECIO"
        assert resultado["precio"] == Decimal("9900")
        assert resultado["lista"].id == lista_general.id


