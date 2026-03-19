# Reglas del Agente ERP

Reglas obligatorias para crear o revisar archivos en este repositorio. La referencia oficial de arquitectura y desarrollo esta en `docs/`.

## Referencias de Arquitectura

Ver documentacion completa en `docs/README.md`.

Documentos clave:
- [Arquitectura Modular ERP](docs/arquitectura_modular_erp.md) - componentes, patrones y estandar de modulos.
- [Autenticacion y Permisos](docs/autenticacion_permisos.md) - JWT, multi-tenant y `permission_action_map`.
- [Auditoria y Trazabilidad](docs/auditoria_trazabilidad.md) - Domain Events, Audit Events y hash chain.
- [Arquitectura de Excepciones](docs/exception_architecture.md) - capas limpias y jerarquia AppError.
- [Guia Practica de Desarrollo](docs/guia_desarrollo.md) - testing, consultas y debugging.
- [Guia Full-Stack de Modulos](docs/fullstack_module_development.md) - implementacion backend + frontend.

## Reglas de Arquitectura Backend

### 1) Excepciones por capas

- Usar capas limpias: dominio/servicios no deben depender de excepciones DRF.
- En servicios, levantar solo subclases de `apps.core.exceptions.AppError`:
  - `BusinessRuleError` (400)
  - `AuthorizationError` (403)
  - `ResourceNotFoundError` (404)
  - `ConflictError` (409)
- Mantener traduccion HTTP en `apps.core.api.exception_handler.custom_exception_handler`.
- No usar `from rest_framework.exceptions import ...` en `apps/**/services/*.py`.
- No usar `raise ValueError(...)` para reglas de negocio.

### 2) Contrato de error

Para errores de negocio (`AppError`), responder con:

```json
{
  "detail": "Mensaje legible",
  "error_code": "ERROR_TYPE_CODE",
  "meta": {}
}
```

Notas:
- `meta` es opcional.
- Si `detail` es dict/list (errores de formulario), mantener estructura original.

### 3) Documentacion en servicios

- Todo metodo nuevo en `apps/**/services/*.py` debe incluir docstring breve en espanol tecnico.
- Si hay logica no obvia (idempotencia, concurrencia, lock, tolerancias), agregar comentario corto en espanol antes del bloque.
- Evitar comentarios redundantes.

### 4) Patrones de servicio

1. Usar `@transaction.atomic` en operaciones multi-paso.
2. Aplicar idempotencia con `idempotency_key` cuando corresponda.
3. Emitir `DomainEventService.record_event()` en cambios funcionales.
4. Encolar integraciones con `OutboxService.enqueue()`.
5. Evitar duplicados con `get_or_create`, `update_or_create` o constraints unicos.

### 5) Permisos en ViewSet

```python
class MiViewSet(TenantViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    permission_modulo = Modulos.MI_MODULO
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "mi_accion": Acciones.CUSTOM,
    }
```

Toda accion personalizada debe mapearse en `permission_action_map`.

## Checklist de Modulo Nuevo (Backend)

### 1) Estructura

```text
apps/nuevo_modulo/
  __init__.py
  apps.py
  admin.py
  models/
    __init__.py
    entidad_principal.py
  services/
    __init__.py
    servicio_principal.py
  api/
    __init__.py
    serializers.py
    views.py
    filters.py (opcional)
  tests/
    __init__.py
    test_models.py
    test_services.py
    test_api.py
  README.md (opcional)
```

### 2) Modelos

- [ ] Entidad principal hereda `BaseModel`.
- [ ] Estados definidos con `choices`.
- [ ] Relaciones con FK explicitas.
- [ ] Indices compuestos en `Meta.indexes` para consultas frecuentes.
- [ ] `__str__` util para debugging.
- [ ] No llamar manualmente `full_clean()` en flujo normal (ya lo hace `BaseModel.save()`).

### 3) Servicios

- [ ] Centralizar logica de negocio en servicios.
- [ ] Docstring en espanol tecnico por metodo.
- [ ] Levantar solo `AppError` subclases.
- [ ] Usar `@transaction.atomic` si hay multiples escrituras.
- [ ] Emitir `DomainEventService.record_event()` en flujos principales.
- [ ] Encolar `OutboxService.enqueue()` para consumidores externos.
- [ ] Agregar comentarios donde haya lock/idempotencia/concurrencia.

### 4) API

- [ ] Heredar `TenantViewSetMixin + ModelViewSet`.
- [ ] Definir `permission_modulo` y `permission_action_map`.
- [ ] Validar entrada en serializers; reglas de negocio en servicios.
- [ ] No recapturar excepciones de negocio en viewset (dejar handler global).
- [ ] Registrar acciones custom con `@action` y mapear permisos.

### 5) Serializers

- [ ] Validacion basica de campos y objeto.
- [ ] Sin logica de negocio compleja.
- [ ] Mantener formato de errores util para frontend.

### 6) Tests

- [ ] Unitarios de servicios (casos felices y errores esperados).
- [ ] API tests (status + payload).
- [ ] Tests de permisos (403 cuando no corresponde acceso).
- [ ] Tests de eventos (DomainEvent + OutboxEvent).

### 7) Permisos

- [ ] Agregar `Modulos.NUEVO_MODULO` en constantes.
- [ ] Agregar `Acciones` nuevas si aplica.
- [ ] Incluir modulo/acciones en `PERMISOS_CATALOGO`.
- [ ] Definir asignacion inicial por rol (fixture/migracion).

### 8) Auditoria

- [ ] Usar `AuditoriaMixin` o `AuditoriaService.registrar_evento()` cuando aplique.
- [ ] Incluir `changes` con antes/despues en cambios relevantes.

## Checklist de Modulo Nuevo (Frontend)

### 1) Estructura

```text
src/modules/nuevo_modulo/
  pages/
    ListPage.jsx
    DetailPage.jsx
    FormPage.jsx
    index.js
  components/
    ItemForm.jsx
    ItemCard.jsx
    StateSelect.jsx
    index.js
  store/
    api.js
    slice.js (opcional)
  tests/
    components.test.jsx
    pages.test.jsx
    api.test.js
  constants.js
  utils.js
  index.js
```

### 2) Paginas

- [ ] `ListPage` con filtros, paginacion, estados de carga/error y acciones.
- [ ] `DetailPage` con vista completa y acciones contextuales.
- [ ] `FormPage` para crear/editar con validaciones.

### 3) Componentes

- [ ] Formularios reutilizables.
- [ ] Tabla/tarjetas para listado.
- [ ] Selectores de estado/referencias.
- [ ] Componente de error para `detail` + `error_code`.

### 4) Hooks y API

- [ ] `useListModulo()`
- [ ] `useDetailModulo(id)`
- [ ] `useCreateModulo()`
- [ ] `useUpdateModulo()`
- [ ] `useDeleteModulo()`
- [ ] `useAction(id, action)`

Usar `frontend/src/api/client.js` para requests y manejar errores del contrato API.

### 5) Permisos en UI

- [ ] Verificar permisos antes de mostrar botones/acciones.
- [ ] Manejar 403 mostrando mensaje claro de acceso denegado.
- [ ] Reflejar el mismo modelo de permisos backend (`Modulos` + `Acciones`).

### 6) Estados y transiciones

- [ ] Mostrar solo acciones permitidas por estado.
- [ ] Deshabilitar acciones invalidas.
- [ ] Mantener consistencia con transiciones backend.

### 7) UX

- [ ] Estados de carga y empty state.
- [ ] Confirmacion para acciones destructivas.
- [ ] Feedback de exito/error.
- [ ] Responsive (movil/tablet).

### 8) Tests frontend

- [ ] Unit tests de componentes y utilidades.
- [ ] Integration tests de flujos principales.
- [ ] Tests de permisos UI.
- [ ] Tests de manejo de errores.

### 9) Preferencia del proyecto

- [ ] Mostrar precios/montos sin decimales en frontend (Chile rollout), aunque backend almacene decimales.

## Ejemplos de Contrato API

### Exito (201)

```json
{
  "id": "uuid",
  "numero_folio": "SOM-000001",
  "estado": "BORRADOR",
  "cliente": { "id": "uuid", "nombre": "..." },
  "items": [],
  "monto_total": 1000
}
```

### Validacion (400)

```json
{
  "detail": { "cliente": ["Este campo es obligatorio."] },
  "error_code": "VALIDATION_ERROR"
}
```

### Regla de negocio (400)

```json
{
  "detail": "No se puede aprobar sin items.",
  "error_code": "BUSINESS_RULE_ERROR"
}
```

### Permiso denegado (403)

```json
{
  "detail": "No tiene permiso para realizar esta accion.",
  "error_code": "PERMISSION_DENIED"
}
```

### No encontrado (404)

```json
{
  "detail": "Recurso no encontrado.",
  "error_code": "RESOURCE_NOT_FOUND"
}
```

### Conflicto (409)

```json
{
  "detail": "Solo se puede editar en estado BORRADOR.",
  "error_code": "CONFLICT"
}
```

## Checklist de Revision de Codigo

### Backend

- [ ] Solo subclases `AppError` en servicios.
- [ ] Docstrings en servicios (espanol tecnico).
- [ ] `@transaction.atomic` donde corresponda.
- [ ] Eventos de dominio/outbox en cambios relevantes.
- [ ] `permission_action_map` completo (incluye acciones custom).
- [ ] Tests de servicio + API + eventos.
- [ ] Sin imports DRF en `services/`.

### Frontend

- [ ] Permisos validados antes de mostrar acciones.
- [ ] Errores backend mostrados correctamente (`detail`, `error_code`).
- [ ] Estados y transiciones coherentes con backend.
- [ ] Tests de listado/crear/editar/error.
- [ ] Comportamiento responsive.

### Compartido

- [ ] Documentacion actualizada (README/docstrings) cuando hay cambios de flujo.
- [ ] Auditoria aplicada en cambios sensibles.
- [ ] Eventos de integracion encolados cuando hay consumidores externos.
