# Estandar de Modulo ERP

## Objetivo

Definir el estandar objetivo para implementar modulos nuevos o refactorizar modulos existentes en este ERP.

Este documento formaliza que el modulo `productos` es la referencia actual del nivel de calidad esperado, tanto en backend como en frontend, y que su estructura debe reutilizarse como patron para el resto del sistema.

## Modulo de referencia

El modulo `productos` se considera el ejemplo base de modulo enterprise del ERP porque consolida:

- maestro de negocio transversal
- servicios de backend con reglas reales y no solo CRUD
- permisos por accion
- trazabilidad, gobernanza y versionado
- integracion con otros modulos operativos
- frontend modular con separacion entre API, hooks, mutaciones y vistas
- tests sobre negocio, permisos e integraciones clave

Referencia funcional:

- `frontend/src/modules/productos/README.md`

## Principios del estandar

Todo modulo nuevo o evolucionado debe aspirar a cumplir estos principios:

1. Ser un modulo de negocio, no solo un CRUD.
2. Centralizar reglas de dominio en servicios backend.
3. Exponer contratos claros hacia frontend y otros modulos.
4. Reflejar permisos y estados de negocio de forma consistente entre backend y frontend.
5. Emitir trazabilidad suficiente para auditoria, soporte e integraciones.
6. Mantener una estructura que permita crecer sin duplicar logica.

## Estandar Backend

### 1. Modelado

- Heredar de `BaseModel` o de las bases documentales cuando corresponda.
- Si el modulo es documental, preferir `DocumentoBase`, `DocumentoTributableBase` y `DocumentoItemBase`.
- Declarar estados explicitos con `choices`.
- Definir indices segun consultas operativas reales.
- Separar maestro, historico y estado operativo cuando el dominio lo requiera.

### 2. Servicios

- Toda regla de negocio vive en `apps/**/services/*.py`.
- Los servicios levantan solo subclases de `AppError`.
- Los metodos nuevos llevan docstring breve en espanol tecnico.
- Los flujos multi-paso usan `@transaction.atomic`.
- Cuando hay concurrencia, locks o reintentos, debe quedar comentario corto explicando la razon.
- Los cambios funcionales relevantes emiten `DomainEventService.record_event()`.
- Las integraciones asincronas usan `OutboxService.enqueue()`.

### 3. API

- ViewSets con `TenantViewSetMixin + ModelViewSet`.
- `permission_modulo` y `permission_action_map` obligatorios.
- Las validaciones basicas viven en serializers.
- Las reglas de negocio viven en servicios.
- El contrato de error debe respetar `{ detail, error_code, meta? }`.

### 4. Integraciones entre modulos

- Cada modulo debe explicitar que consume de otros modulos y que expone.
- Las integraciones no deben depender de campos de conveniencia si existe un endpoint o servicio de dominio mas preciso.
- Ejemplo de estandar:
  - `ventas` debe resolver precio comercial via `productos`
  - `compras` usa `productos` como maestro y sugerencia de catalogo, pero define su precio segun proveedor o documento
  - `inventario` usa configuracion y costo del producto, no pricing comercial

### 5. Testing backend

- Tests de servicio para casos felices, conflictos y reglas de negocio.
- Tests API para status, payload y permisos.
- Tests de integracion cuando el modulo impacta a otros modulos.
- Tests de eventos cuando el flujo emite `DomainEvent` u `OutboxEvent`.

## Estandar Frontend

### 1. Estructura

Cada modulo frontend debe acercarse a esta organizacion:

```text
src/modules/modulo/
  pages/
  components/
  store/
    api.js
    hooks.js
    mutations.js
    slice.js (solo si realmente hay estado compartido)
  services/
  tests/
  README.md
```

### 2. Criterio de estado

No todo debe ir a slices.

Regla oficial:

- `slice`
  Para estado compartido, transversal y reutilizado por varias vistas.
- `hooks`
  Para lecturas ligadas a una vista o flujo concreto.
- `mutations`
  Para acciones create/update/delete/custom con toasts, manejo de errores y refresh.

Se debe evitar que el mismo recurso tenga dos fuentes de verdad activas sin una razon clara.

### 3. Permisos y estados UI

- La UI debe ocultar o deshabilitar acciones sin permiso.
- La UI debe respetar restricciones por estado del documento o entidad.
- Los mensajes de acceso denegado y conflicto deben ser claros.
- El frontend debe representar el mismo modelo de permisos que backend.

### 4. Manejo de errores

- Mostrar `detail` y `error_code` del backend cuando exista contrato.
- Evitar duplicar manejo de errores en cada pagina si puede centralizarse.
- Las mutaciones deben encapsular toasts y normalizacion del error.

### 5. Testing frontend

- Tests de permisos UI.
- Tests de manejo de errores backend.
- Tests de flujos create/edit/delete.
- Tests de integracion cuando la pantalla consuma contratos de otro modulo.

## Criterios enterprise que todo modulo debe cumplir

Un modulo se considera en estandar ERP enterprise cuando cumple, como minimo, con esto:

- tiene reglas de negocio reales centralizadas en servicios
- expone permisos por accion y los replica en UI
- diferencia entre datos maestros, estado operativo e historico si el dominio lo requiere
- tiene integraciones declaradas con otros modulos
- cubre casos de error y permisos con tests
- cuenta con documentacion local y referencia en `docs/`

## Productos como patron concreto

Hoy `productos` debe tomarse como el patron de referencia en estas decisiones:

- maestro transversal del ERP
- pricing comercial resuelto por endpoint de dominio, no por campos duplicados en UI
- trazabilidad y gobernanza del maestro separadas del stock operativo
- frontend con `api.js`, `hooks.js`, `mutations.js` y criterio mixto `slice vs hooks`
- integraciones explicitas con `ventas`, `compras` e `inventario`

## Uso esperado para futuros modulos

Cuando se implemente o refactorice un modulo nuevo, se espera:

1. Revisar `docs/arquitectura_modular_erp.md`
2. Revisar `docs/fullstack_module_development.md`
3. Revisar este documento como estandar objetivo
4. Comparar la estructura propuesta con el modulo `productos`
5. Documentar cualquier desviacion intencional

## Desviaciones aceptables

No todos los modulos deben copiar literalmente a `productos`. Se aceptan diferencias cuando:

- el dominio es mucho mas simple y no requiere slice, cache o analitica
- el modulo no es documental
- no hay integraciones transversales relevantes
- el costo de una abstraccion extra supera su beneficio real

Si hay desviacion, debe estar justificada en el README del modulo o en la documentacion tecnica correspondiente.
