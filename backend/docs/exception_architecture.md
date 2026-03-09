# Exception Architecture (Clean Layers)

This project uses an exception abstraction to keep clean boundaries across layers.

## Layer Rules

1. Domain/Model layer:
- Raise domain/app exceptions from `apps.core.exceptions` for business constraints.
- Do not raise DRF exceptions here.

2. Service/Application layer (`apps/**/services/*.py`):
- Raise only app exceptions (`AppError` subclasses).
- Do not import `rest_framework.exceptions`.
- Do not import `django.core.exceptions.ValidationError` for service logic.

3. API layer (`apps/**/api/*.py`):
- Validate request input with serializers.
- Let app exceptions bubble up.
- Use global handler (`apps.core.api.exception_handler.custom_exception_handler`) to map to HTTP.

4. Frontend/API clients:
- Consume `detail` as human message.
- Optionally consume `error_code` for deterministic UX rules.

## Standard Error Payload

For `AppError` with string detail:

```json
{
  "detail": "No tiene permisos para aprobar presupuestos.",
  "error_code": "AUTHORIZATION_ERROR",
  "meta": {}
}
```

Notes:
- `meta` is optional and present only when provided.
- If `detail` is field-oriented (`dict`/`list`), payload shape is preserved for forms.

## Canonical Exception Types

- `BusinessRuleError` -> 400
- `AuthorizationError` -> 403
- `ResourceNotFoundError` -> 404
- `ConflictError` -> 409
- `AppError` -> 400 (base/fallback)

## File Creation/Review Checklist

When creating or reviewing new modules/files:

1. Services use only app exceptions.
2. Services do not import DRF exceptions.
3. Services do not raise `ValueError` for business logic.
4. API code does not duplicate try/except HTTP mapping already handled globally.
5. Tests assert app exception classes in service tests.
6. API tests assert HTTP status and payload (`detail`, `error_code` when applicable).

## Quick Example

```python
from apps.core.exceptions import AuthorizationError, BusinessRuleError

if not user.tiene_permiso(...):
    raise AuthorizationError("No tiene permisos para ejecutar esta accion.")

if cantidad <= 0:
    raise BusinessRuleError("La cantidad debe ser mayor a cero.")
```
