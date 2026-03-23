import pytest
from datetime import date

from apps.productos.models import ListaPrecio
from apps.tesoreria.models import Moneda


@pytest.mark.django_db
def test_lista_precio_normaliza_nombre_a_mayusculas(empresa, usuario):
    moneda = Moneda.all_objects.get(empresa=empresa, codigo="CLP")

    lista = ListaPrecio.objects.create(
        empresa=empresa,
        creado_por=usuario,
        nombre="  Lista mayorista norte  ",
        moneda=moneda,
        fecha_desde=date(2026, 1, 1),
        activa=True,
        prioridad=100,
    )

    assert lista.nombre == "LISTA MAYORISTA NORTE"
