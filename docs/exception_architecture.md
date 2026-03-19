# Arquitectura de Excepciones (Capas Limpias)

Este proyecto usa una abstraccion de excepciones para mantener limites claros entre capas.

## Reglas por Capa

1. Capa de dominio/modelo:
- Levantar excepciones de dominio/aplicacion desde `apps.core.exceptions` para restricciones de negocio.
- No levantar excepciones de DRF aqui.

2. Capa de servicio/aplicacion (`apps/**/services/*.py`):
- Levantar solo excepciones de aplicacion (subclases de `AppError`).
- No importar `rest_framework.exceptions`.
- No importar `django.core.exceptions.ValidationError` para logica de servicios.

3. Capa API (`apps/**/api/*.py`):
- Validar entrada con serializers.
- Permitir que las excepciones de aplicacion se propaguen.
- Usar handler global (`apps.core.api.exception_handler.custom_exception_handler`) para mapear a HTTP.

4. Frontend/consumidores API:
- Consumir `detail` como mensaje legible.
- Opcionalmente consumir `error_code` para reglas UX deterministicas.

## Payload Estandar de Error

Para `AppError` con `detail` de tipo string:

```json
{
  "detail": "No tiene permisos para aprobar presupuestos.",
  "error_code": "AUTHORIZATION_ERROR",
  "meta": {}
}
```

Notas:
- `meta` es opcional y solo aparece si fue enviado.
- Si `detail` es de tipo `dict` o `list`, se preserva su forma para formularios.

## Tipos Canonicos de Excepcion

- `BusinessRuleError` -> 400
- `AuthorizationError` -> 403
- `ResourceNotFoundError` -> 404
- `ConflictError` -> 409
- `AppError` -> 400 (base/fallback)

## Checklist de Creacion/Revision de Archivos

Al crear o revisar modulos/archivos nuevos:

1. Servicios usan solo excepciones de aplicacion.
2. Servicios no importan excepciones DRF.
3. Servicios no levantan `ValueError` para logica de negocio.
4. API no duplica mapeo try/except HTTP que ya hace el handler global.
5. Tests de servicios validan clases de excepcion de aplicacion.
6. Tests de API validan status HTTP y payload (`detail`, `error_code` cuando aplique).

## Ejemplo Rapido

```python
from apps.core.exceptions import AuthorizationError, BusinessRuleError

if not user.tiene_permiso(...):
    raise AuthorizationError("No tiene permisos para ejecutar esta accion.")

if cantidad <= 0:
    raise BusinessRuleError("La cantidad debe ser mayor a cero.")
```
