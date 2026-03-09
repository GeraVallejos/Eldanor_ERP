import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.exceptions import AppError


logger = logging.getLogger(__name__)


def _as_response_detail(detail):
    if isinstance(detail, (dict, list)):
        return detail
    return {"detail": str(detail)}


def _app_error_payload(exc):
    detail = exc.detail
    if isinstance(detail, (dict, list)):
        # Keep field-oriented payload shape for forms.
        return detail

    payload = {
        "detail": str(detail),
        "error_code": exc.error_code,
    }
    if exc.meta is not None:
        payload["meta"] = exc.meta
    return payload


def custom_exception_handler(exc, context):
    # Keep DRF/SimpleJWT native behavior first.
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, AppError):
        return Response(_app_error_payload(exc), status=exc.status_code)

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            detail = exc.message_dict
        elif hasattr(exc, "messages"):
            detail = exc.messages
        else:
            detail = str(exc)
        return Response(_as_response_detail(detail), status=status.HTTP_400_BAD_REQUEST)

    logger.exception("Unhandled exception in API", exc_info=exc)
    return Response(
        {
            "detail": "Ocurrio un error interno del servidor.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
