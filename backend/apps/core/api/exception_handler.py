import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.exceptions import AppError


logger = logging.getLogger(__name__)


ERROR_CODE_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
    status.HTTP_401_UNAUTHORIZED: "NOT_AUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "PERMISSION_DENIED",
    status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


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


def _drf_error_code(exc, response):
    if isinstance(exc, drf_exceptions.NotAuthenticated):
        return "NOT_AUTHENTICATED"
    if isinstance(exc, drf_exceptions.AuthenticationFailed):
        return "AUTHENTICATION_FAILED"
    if isinstance(exc, drf_exceptions.PermissionDenied):
        return "PERMISSION_DENIED"
    if isinstance(exc, drf_exceptions.NotFound):
        return "RESOURCE_NOT_FOUND"
    if isinstance(exc, drf_exceptions.MethodNotAllowed):
        return "METHOD_NOT_ALLOWED"
    if isinstance(exc, drf_exceptions.Throttled):
        return "RATE_LIMITED"
    if isinstance(exc, drf_exceptions.ValidationError):
        return "VALIDATION_ERROR"
    return ERROR_CODE_BY_STATUS.get(response.status_code, "API_ERROR")


def _normalize_drf_response(exc, response):
    data = response.data
    if isinstance(data, dict) and "error_code" in data:
        return response

    error_code = _drf_error_code(exc, response)

    if isinstance(data, dict):
        detail = data.get("detail", data)
        if isinstance(detail, (dict, list)):
            payload = {
                "detail": detail,
                "error_code": error_code,
            }
            meta = {
                key: value
                for key, value in data.items()
                if key not in {"detail", "error_code"}
            }
            if meta:
                payload["meta"] = meta
            response.data = payload
            return response

        payload = {
            "detail": str(detail),
            "error_code": error_code,
        }
        meta = {
            key: value
            for key, value in data.items()
            if key not in {"detail", "error_code"}
        }
        if meta:
            payload["meta"] = meta
        response.data = payload
        return response

    if isinstance(data, list):
        response.data = {
            "detail": data,
            "error_code": error_code,
        }
        return response

    response.data = {
        "detail": str(data),
        "error_code": error_code,
    }
    return response


def custom_exception_handler(exc, context):
    # Keep DRF/SimpleJWT native behavior first, but normalize payload shape.
    response = drf_exception_handler(exc, context)
    if response is not None:
        return _normalize_drf_response(exc, response)

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
