import pytest
from apps.core.models import Empresa
from apps.core.models.secuencia import SecuenciaDocumento
from apps.core.services.secuencia_service import SecuenciaService   


@pytest.mark.django_db
def test_creacion_empresa_crea_secuencia():

    empresa = Empresa.objects.create(nombre="Empresa Test")

    secuencia = SecuenciaDocumento.all_objects.filter(
        empresa=empresa,
        tipo_documento="PRESUPUESTO"
    ).first()

    assert secuencia is not None
    assert secuencia.ultimo_numero == 0



@pytest.mark.django_db
def test_secuencia_incrementa():

    empresa = Empresa.objects.create(nombre="Empresa Test")

    numero1 = SecuenciaService.obtener_siguiente_numero(
        empresa, "PRESUPUESTO"
    )

    numero2 = SecuenciaService.obtener_siguiente_numero(
        empresa, "PRESUPUESTO"
    )

    assert numero1 == 1
    assert numero2 == 2