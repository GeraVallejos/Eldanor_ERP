import pytest
from django.core.exceptions import ValidationError

from apps.core.validators import formatear_rut, validar_rut_con_dv


@pytest.mark.django_db
class TestRutValidators:
    def test_formatear_rut_desde_valor_sin_puntos(self):
        assert formatear_rut("123456785") == "12.345.678-5"

    def test_validar_rut_con_dv_acepta_rut_valido(self):
        validar_rut_con_dv("12.345.678-5")

    def test_validar_rut_con_dv_rechaza_dv_invalido(self):
        with pytest.raises(ValidationError):
            validar_rut_con_dv("12.345.678-9")
