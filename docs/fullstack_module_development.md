# Guia Full-Stack de Desarrollo de Modulos

Antes de usar esta guia, revisar tambien [Estandar de Modulo ERP](modulo_estandar_erp.md). Esta guia explica el proceso; el estandar define la calidad y estructura objetivo, tomando `productos` como modulo de referencia.

Este documento describe como implementar un modulo completo, backend Django + frontend React, manteniendo sincronizacion entre capas.

## Flujo recomendado

### 1. Planificacion

- Definir modelo de negocio.
- Definir estados y transiciones.
- Definir permisos por accion.
- Definir eventos de dominio e integraciones requeridas.
- Confirmar si el modulo es maestro, documental u operativo.

### 2. Backend

#### Modelos

- Heredar de `BaseModel` o de las bases documentales.
- Declarar indices segun consultas reales.
- Separar historico y estado operativo cuando el dominio lo requiera.

#### Servicios

- Centralizar toda regla de negocio en `apps/**/services/*.py`.
- Usar solo subclases de `AppError`.
- Agregar docstrings breves en espanol tecnico.
- Usar `@transaction.atomic` en flujos multi-paso.
- Emitir `DomainEventService.record_event()` y `OutboxService.enqueue()` cuando corresponda.

#### API

- Usar `TenantViewSetMixin + ModelViewSet`.
- Declarar `permission_modulo` y `permission_action_map`.
- Dejar validacion de negocio en servicios.
- Mantener el contrato de error uniforme.

#### Tests backend

- Tests de servicio.
- Tests API.
- Tests de permisos.
- Tests de eventos e integraciones.

### 3. Frontend

#### Estructura recomendada

```text
src/modules/modulo/
  pages/
  components/
  store/
    api.js
    hooks.js
    mutations.js
    slice.js (solo si hay estado compartido real)
  services/
  tests/
  README.md
```

#### Reglas frontend

- Validar permisos antes de mostrar acciones.
- Reflejar restricciones por estado.
- Mostrar errores backend con `detail` y `error_code`.
- Separar llamadas API, lecturas y mutaciones.
- Evitar duplicar la misma fuente de verdad entre `slice` y hooks.

#### Tests frontend

- Tests de permisos UI.
- Tests de manejo de errores.
- Tests de create, edit y delete.
- Tests de integracion cuando la pantalla consuma contratos de otro modulo.

### 4. Integracion

- Declarar que consume el modulo desde otros modulos.
- Declarar que expone el modulo hacia otros modulos.
- Evitar depender de campos de conveniencia si existe un endpoint o servicio de dominio mas preciso.
- Documentar contratos operativos e integraciones relevantes.

### 5. Documentacion

- Crear README local del modulo si tiene complejidad relevante.
- Registrar el modulo en `docs/` si define un patron o flujo importante.
- Documentar desviaciones intencionales respecto del estandar.

## Regla principal

El proceso de esta guia siempre debe cruzarse con [Estandar de Modulo ERP](modulo_estandar_erp.md). La guia explica como avanzar; el estandar define como debe verse el resultado final.
