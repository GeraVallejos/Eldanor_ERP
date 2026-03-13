from datetime import date
from decimal import Decimal

import pytest

from apps.contactos.models import Cliente, Contacto
from apps.core.models import Moneda
from apps.core.services import TipoCambioService
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
            rut="14141414-1",
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
