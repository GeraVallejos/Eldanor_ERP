from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.test import APIRequestFactory

from apps.core.api.exception_handler import custom_exception_handler
from apps.core.exceptions import BusinessRuleError


factory = APIRequestFactory()


def _context():
    return {"request": factory.get("/api/test/"), "view": None}


def test_app_error_con_detail_dict_incluye_error_code():
    response = custom_exception_handler(
        BusinessRuleError(
            {"cliente": ["Este campo es obligatorio."]},
            error_code="BUSINESS_RULE_ERROR",
        ),
        _context(),
    )

    assert response.status_code == 400
    assert response.data == {
        "detail": {"cliente": ["Este campo es obligatorio."]},
        "error_code": "BUSINESS_RULE_ERROR",
    }


def test_django_validation_error_dict_respeta_contrato_api():
    response = custom_exception_handler(
        DjangoValidationError({"rut": ["Formato invalido."]}),
        _context(),
    )

    assert response.status_code == 400
    assert response.data == {
        "detail": {"rut": ["Formato invalido."]},
        "error_code": "VALIDATION_ERROR",
    }
