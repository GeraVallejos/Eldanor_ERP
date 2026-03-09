# ERP Agent Rules

These rules are mandatory when creating or reviewing files in this repository.

## Exception Architecture

- Use clean layers: domain/services must not depend on DRF exception classes.
- In services, raise only `apps.core.exceptions.AppError` subclasses.
- Keep HTTP translation in `apps.core.api.exception_handler.custom_exception_handler`.

## New Module Checklist

1. Service methods raise `BusinessRuleError`, `AuthorizationError`, `ResourceNotFoundError`, or `ConflictError`.
2. No `from rest_framework.exceptions import ...` in `apps/**/services/*.py`.
3. No `raise ValueError(...)` for business rule failures in service/domain flows.
4. API endpoints rely on serializer validation + global exception handler.
5. Add/adjust tests for both service exception type and API response contract.

## Error Contract

For app exceptions with text detail, API responses should include:
- `detail`
- `error_code`
- optional `meta`

Field-level validation payloads (dict/list) should remain unchanged to preserve form UX.
