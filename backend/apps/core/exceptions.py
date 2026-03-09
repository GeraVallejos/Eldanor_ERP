class AppError(Exception):
    """Base exception for application/domain errors.

    Services and domain code should raise these exceptions instead of
    framework-specific exceptions.
    """

    status_code = 400
    default_detail = "Se produjo un error de aplicacion."
    default_error_code = "APP_ERROR"

    def __init__(self, detail=None, *, error_code=None, meta=None):
        self.detail = detail if detail is not None else self.default_detail
        self.error_code = error_code or self.default_error_code
        self.meta = meta
        super().__init__(str(self.detail))


class BusinessRuleError(AppError):
    """Raised when a business rule is violated."""

    status_code = 400
    default_detail = "La operacion no cumple las reglas de negocio."
    default_error_code = "BUSINESS_RULE_ERROR"


class AuthorizationError(AppError):
    """Raised when the current user lacks permission for the action."""

    status_code = 403
    default_detail = "No tiene permisos para ejecutar esta accion."
    default_error_code = "AUTHORIZATION_ERROR"


class ResourceNotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    default_detail = "Recurso no encontrado."
    default_error_code = "RESOURCE_NOT_FOUND"


class ConflictError(AppError):
    """Raised when the request conflicts with current resource state."""

    status_code = 409
    default_detail = "Conflicto con el estado actual del recurso."
    default_error_code = "CONFLICT_ERROR"
