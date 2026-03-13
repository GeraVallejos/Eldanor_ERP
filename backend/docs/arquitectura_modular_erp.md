# Arquitectura Modular ERP (Base Tecnica)

## Objetivo
Definir una base estable para incorporar modulos (Ventas, Contaduria, Tesoreria, etc.) sin reescribir logica transversal de negocio.

## Principios de arquitectura
- Multi-tenant por empresa: todo agregado de negocio hereda de `BaseModel` y queda asociado a una empresa.
- Servicios como capa de negocio: las reglas viven en `apps/**/services/*.py`.
- Contrato de excepciones uniforme: dominio/servicios usan `AppError` y subclases.
- API desacoplada: DRF traduce excepciones mediante el handler global.
- Trazabilidad por eventos: cambios relevantes publican `DomainEvent` + `OutboxEvent`.
- Idempotencia: operaciones integrables usan `idempotency_key` o `dedup_key`.

## Componentes transversales

### 1) WorkflowService
Archivo: `apps/core/services/workflow_service.py`

Responsabilidad:
- Normalizar y validar transiciones de estado.
- Evitar reglas duplicadas de flujo por modulo.

Funciones:
- `normalize_state(value)`: normaliza estado a formato canonico.
- `allowed_next(current_state, transitions)`: retorna estados permitidos.
- `assert_transition(...)`: valida transicion y retorna destino.
- `apply_transition(...)`: aplica y persiste transicion valida.

Uso recomendado:
- Cada modulo declara su matriz de transiciones (`ESTADOS_TRANSICION_VALIDA`) y delega validacion en este servicio.

### 2) DomainEventService
Archivo: `apps/core/services/domain_event_service.py`

Responsabilidad:
- Registrar eventos de dominio append-only para auditoria funcional.

Funcion principal:
- `record_event(...)`: persiste evento con payload/meta, con idempotencia opcional.

Modelo asociado:
- `DomainEvent` (`apps/core/models/domain_event.py`).

### 3) OutboxService
Archivo: `apps/core/services/outbox_service.py`

Responsabilidad:
- Implementar patron Outbox para integraciones asincronas confiables.

Funciones:
- `enqueue(...)`: encola evento de integracion.
- `claim_pending(...)`: toma eventos pendientes con lock.
- `mark_sent(...)`: marca entrega exitosa.
- `mark_failed(...)`: marca fallo y agenda reintento.
- `requeue_failed(...)`: reprocesa lote de fallidos.

Modelo asociado:
- `OutboxEvent` (`apps/core/models/outbox_event.py`).

### 4) AccountingBridge
Archivo: `apps/core/services/accounting_bridge.py`

Responsabilidad:
- Puente de negocio -> contabilidad sin acoplar modulos a implementacion contable.

Funcion principal:
- `request_entry(...)`: publica `DomainEvent` y `OutboxEvent` para asiento contable.

## Acoplamiento entre modulos

### Flujo actual presupuesto -> integraciones
1. `PresupuestoService` registra cambio de estado.
2. Se persiste `PresupuestoHistorial`.
3. Se emite `DomainEvent` de estado.
4. Se encola `OutboxEvent` de notificacion de cambio.

Archivos:
- `apps/presupuestos/services/presupuesto_service.py`
- `apps/core/services/domain_event_service.py`
- `apps/core/services/outbox_service.py`

### Flujo actual inventario -> integraciones
1. `InventarioService.registrar_movimiento` valida reglas.
2. Actualiza stock, costo promedio y snapshot.
3. Emite `DomainEvent` de movimiento.
4. Encola `OutboxEvent` para consumidores externos.

Archivo:
- `apps/inventario/services/inventario_service.py`

## Modelo de negocio base (resumen)

### Multiempresa
- Cada registro operativo pertenece a una empresa.
- El middleware de tenant inyecta el contexto de empresa activa.

### Documentos y folios
- Las secuencias por empresa se gestionan en `SecuenciaService`.
- El sistema soporta tipos de documento de compras y ventas para crecer por dominio.

### Inventario
- Stock valorizado por bodega.
- Reservas de stock por documento para evitar sobreventa.
- Movimientos con trazabilidad documental y snapshots historicos.

### Seguridad
- Auth JWT via cookies HttpOnly.
- CSRF reforzado para refresh por cookie.
- Permisos por modulo/accion y empresa activa.

## Estandar para nuevos modulos
Para un modulo nuevo (`ventas`, `tesoreria`, `contabilidad`):
1. Definir entidades con `BaseModel`.
2. Centralizar reglas en `services` con excepciones de dominio.
3. Definir matriz de estados y validar con `WorkflowService`.
4. Emitir `DomainEvent` en cambios relevantes.
5. Publicar `OutboxEvent` para integraciones.
6. Agregar tests de servicio, API y eventos.

## Convenciones de documentacion tecnica
- Todo metodo nuevo en `apps/**/services/*.py` debe incluir docstring breve en espanol tecnico.
- Si existe logica no obvia (idempotencia, concurrencia, locks, tolerancias), agregar comentario corto en espanol.
- Evitar comentarios redundantes.

## Publicacion en GitHub Pages
Sugerencia:
- Exponer `backend/docs/` dentro del sitio de documentacion.
- Mantener esta pagina como indice tecnico de arquitectura.
- Crear paginas por modulo (`ventas.md`, `tesoreria.md`, `contabilidad.md`) usando esta estructura.
