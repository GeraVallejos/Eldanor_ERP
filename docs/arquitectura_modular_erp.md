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

Seis servicios reutilizables centralizan logica transversal. Todos estan en `apps/core/services/` con importacion en `__init__.py`.

### 1) WorkflowService
Archivo: `apps/core/services/workflow_service.py`

Responsabilidad:
- Normalizar y validar transiciones de estado.
- Evitar reglas duplicadas de flujo por modulo.

Metodos principales:
- `normalize_state(value)`: normaliza estado a mayusculas (ej. "draft" -> "BORRADOR").
- `allowed_next(current_state, transitions)`: retorna lista de estados permitidos desde current_state.
- `assert_transition(current_state, next_state, transitions)`: valida transicion y retorna destino normalizado; levanta `BusinessRuleError` si no es valida.
- `apply_transition(instance, next_state, transitions)`: aplica, persiste cambio en `estado` field y retorna instancia.

Uso recomendado:
- Cada modulo declara su matriz `ESTADOS_TRANSICION_VALIDA = { "BORRADOR": ["ENVIADO", "CANCELADO"], ... }` y delega validacion.
- Ejemplo: `PresupuestoService.aprobar_presupuesto()` usa `WorkflowService.apply_transition()` atomicamente.

### 2) DomainEventService
Archivo: `apps/core/services/domain_event_service.py`

Responsabilidad:
- Registrar eventos de dominio append-only para auditoria funcional y fuente de verdad.
- Deduplicacion por `idempotency_key` para garantizar exactitud-una entrega.

Metodo principal:
- `record_event(empresa, aggregate_type, aggregate_id, event_type, payload, meta=None, idempotency_key=None, usuario=None, event_version=1)`: 
  - Persiste evento inmutable.
  - Si `idempotency_key` existe, retorna evento existente (dedup).
  - Levanta `BusinessRuleError` si campos requeridos faltan.
  - Registra `usuario` si se proporciona.

Modelo asociado:
- `DomainEvent` (`apps/core/models/domain_event.py`): agregado_tipo, agregado_id, tipo_evento, payload, meta, idempotency_key, evento_version.
- Append-only: nunca se actualiza o borra.

Diferencia clave: `DomainEventService` es **funcional** (negocio). No determina integracion con sistemas externos.

### 3) OutboxService
Archivo: `apps/core/services/outbox_service.py`

Responsabilidad:
- Implementar patron Outbox para integraciones asincronas confiables sin acoplos directos.
- Garantizar exactitud-una entrega incluso si consumer falla.

Metodos principales:
- `enqueue(empresa, event_type, payload, meta=None, idempotency_key=None, consumer_name=None)`: encola evento de integracion en estado PENDING con dedup.
- `claim_pending(empresa, batch_size=100, consumer_name=None)`: toma eventos PENDING con `select_for_update()` (lock pessimista), cambia a PROCESSING, retorna batch.
- `mark_sent(event_ids)`: cambia status a SENT (entrega exitosa).
- `mark_failed(event_id, error_message, retry_after_minutes=None)`: cambia status a FAILED, registra error y agenda reintento.
- `requeue_failed(empresa, batch_size=100, consumer_name=None)`: reprocesa lote de FAILED si retry_after ha pasado.

Modelo asociado:
- `OutboxEvent` (`apps/core/models/outbox_event.py`): tipo_evento, payload, meta, status (PENDING/PROCESSING/SENT/FAILED), idempotency_key, error_message, retry_after.
- Estados: PENDING -> PROCESSING -> (SENT | FAILED) -> si FAILED y retry_after pasado -> PENDING.

Diferencia clave: `OutboxService` es **tecnico** (integracion). Responsable de envios a consumidores (colas, webhooks, APIs externas).

### 4) SecuenciaService
Archivo: `apps/core/services/secuencia_service.py`

Responsabilidad:
- Generar folios unicos y secuenciales por empresa, tipo documento y bodega.
- Evitar colisiones y permitir gaps controlados (si hay cancelaciones).

Metodos principales:
- `obtener_numero_siguiente_disponible(empresa, tipo_documento, bodega=None)`: retorna preview del siguiente numero SIN reservarlo (lee `ultimo_numero` + 1).
- `obtener_siguiente_numero(empresa, tipo_documento, bodega=None)`: reserva atomicamente siguiente numero con prefijo y padding.
  - Usa `@transaction.atomic` + `select_for_update()` para garantizar unicidad secuencial.
  - Retorna folio con formato `{prefijo}{numero_paddeado}` (ej. "FAC-000001").

Modelo asociado:
- `SecuenciaDocumento`: tipo_documento, bodega (opcional), ultimo_numero, prefijo, padding, empresa.

Uso recomendado:
- En `PresupuestoService.crear_presupuesto()`: antes de guardar, llamar `SecuenciaService.obtener_siguiente_numero()` para asignar `numero_folio`.
- Manejo de reintentos en API: si `select_for_update()` falla por timeout, ViewSet reintenta N veces.

### 5) TipoCambioService
Archivo: `apps/core/services/tipo_cambio_service.py`

Responsabilidad:
- Gestionar tasas de cambio por moneda, fecha y empresa.
- Permitir conversiones de montos con fallback bidireccional.

Metodos principales:
- `registrar_tipo_cambio(empresa, moneda_origen, moneda_destino, tasa, fecha=None)`: registra o actualiza tasa vigente.
  - Valida que ambas monedas pertenezcan a la empresa.
- `obtener_tasa(empresa, moneda_origen, moneda_destino, fecha=None)`: obtiene tasa vigente.
  - Si no existe tasa directa A->B, intenta B->A reciprocal (1/tasa inversa).
  - Usa fecha vigente o anterior mas proxima.
- `convertir_monto(empresa, monto, moneda_origen, moneda_destino, fecha=None, precision_decimal=2)`: convierte monto respetando tasa y decimal.

Uso recomendado:
- En `OrdenCompraService`: si documento es en moneda extranjera, convertir a moneda base para reportes.
- Mantener tasas actualizadas diariamente (cron job o feed externo).

### 6) CarteraService
Archivo: `apps/core/services/cartera_service.py`

Responsabilidad:
- Gestionar cuentas por pagar (CxP) y cuentas por cobrar (CxC).
- Aplicar pagos, calcular vencimiento, mantener estado de deuda.
- Idempotencia: evitar registros duplicados si se reintenta.

Metodos principales:
- `registrar_cxp_desde_documento_compra(empresa, documento_compra, idempotency_key=None)`: 
  - Crea CxP desde factura/guia de compra con referencia estable.
  - Si existe con mismo idempotency_key, retorna existente (no duplica).
  - Estados posibles: PENDIENTE, VENCIDA, PAGADA, PARCIAL.
- `registrar_cxc_manual(empresa, contacto, monto, descripcion, fecha_vencimiento, idempotency_key=None)`: registra CxC manual con dedup.
- `aplicar_pago_cuenta(empresa, cuenta_id, monto_pagado, fecha_pago=None, referencia_pago=None)`: 
  - Aplica pago parcial o total.
  - Recalcula estado (PENDIENTE/VENCIDA/PAGADA/PARCIAL).
  - Retorna saldo pendiente.
- `obtener_estado_deuda(empresa, contacto)`: retorna resumen CxC + CxP agrupado.

Modelo asociado:
- `CuentaPorPagar`, `CuentaPorCobrar` con campos: referencia (documento/manual), monto_original, monto_pagado, estado, fecha_vencimiento, fecha_pago.

Uso recomendado:
- Al crear factura de compra: llamar `registrar_cxp_desde_documento_compra()` con idempotency_key basada en documento_id.
- Al aplicar pago manualmente (tesoreria): llamar `aplicar_pago_cuenta()` y emitir `OutboxEvent` para contabililidad.

### 7) AccountingBridge
Archivo: `apps/core/services/accounting_bridge.py`

Responsabilidad:
- Puente desacoplado de negocio -> contabilidad.
- Evitar que servicios de negocio conozcan detalles de implementacion contable.
- Garantizar exactitud-una entrega de asientos contables (idempotencia con prefixes distintos).

Metodo principal:
- `request_entry(empresa, numero_referencia, tipo_entrada, conceptos, meta=None)`:
  - Publica en dos capas con idempotency_keys estratificados:
    1. `DomainEventService.record_event(...)` con `idempotency_key = f"domain:{numero_referencia}"` -> garantiza un evento de dominio.
    2. `OutboxService.enqueue(...)` con `idempotency_key = f"outbox:{numero_referencia}"` -> encola asiento para consumer contable.
  - Retorna evento de dominio creado.

Flujo de ejemplo:
```
AprobacionPresupuesto (negocio) 
  -> AccountingBridge.request_entry(concepto="Reserva de presupuesto", meta={presupuesto_id})
    -> DomainEventService crea evento funcional
    -> OutboxService encola evento para consumer contable
    -> Consumer (async) consume OutboxEvent y crea asiento real en contabilidad
```

Diferencia clave: Decoupling total entre dominio (presupuestos, inventario, compras) y implementacion contable.

## Acoplamiento entre modulos (Flujos integrados)

La arquitectura usa dos capas de eventos para garantizar trazabilidad funcional + integraciones confiables sin acoplos.

### Capa 1: Eventos de dominio (Trazabilidad funcional)
- `DomainEventService.record_event()` registra evento funcional append-only.
- Usado para auditoria, compliance, trazabilidad de cambios.
- No conoce detalles de integracion externa.
- `idempotency_key` prefixado con `"domain:"` para evitar duplicados.

### Capa 2: Outbox (Integracion asincrona confiable)
- `OutboxService.enqueue()` encola evento para consumidor externo.
- Garantiza exactitud-una entrega incluso si consumer falla.
- Estados: PENDING -> PROCESSING -> SENT (o FAILED -> reintento).
- `idempotency_key` prefixado con `"outbox:"` independiente de dominio.

### Flujo ejemplo: Cambio de estado en presupuesto
```
1. Usuario aprueba presupuesto via API

2. PresupuestoViewSet.aprobar() 
   -> PresupuestoService.aprobar_presupuesto()
      -> WorkflowService.apply_transition(estado="APROBADO")
      -> Presupuesto.save()

3. Despues de save(), emitir eventos:
   a) DomainEventService.record_event(
        aggregate_type="Presupuesto",
        aggregate_id=presupuesto.id,
        event_type="PRESUPUESTO_APROBADO",
        payload={...presupuesto_data...},
        idempotency_key=f"domain:presupuesto_{presupuesto.id}_aprobado"
      )
      -> Persiste evento funcional inmutable

   b) OutboxService.enqueue(
        event_type="PRESUPUESTO_APROBADO",
        payload={...},
        idempotency_key=f"outbox:presupuesto_{presupuesto.id}_notificacion",
        consumer_name="notificaciones"  # Consumer que enviara email/SMS
      )
      -> Encola en status PENDING

4. Consumer asincrono consume OutboxEvent:
   - OutboxService.claim_pending() con select_for_update()
   - Procesa evento (envio email, publicacion a MQ, etc.)
   - OutboxService.mark_sent() o mark_failed() segun resultado
   - Si mark_failed(), automaticamente reagendado con backoff exponencial

5. DomainEvent queda registrado para compliance/auditoria.
```

Archivos involucrados:
- `apps/presupuestos/services/presupuesto_service.py` — Logica de negocio
- `apps/core/services/domain_event_service.py` — Persistencia funcional
- `apps/core/services/outbox_service.py` — Integraciones asincronas
- `apps/core/models/domain_event.py`, `outbox_event.py` — Modelos

### Flujo ejemplo: Movimiento de inventario

```
1. InventarioService.registrar_movimiento(producto, bodega, cantidad, tipo=ENTRADA/SALIDA)

2. Valida reglas:
   - _validar_trazabilidad_producto()
   - _aplicar_trazabilidad_lote() si aplica
   - _aplicar_trazabilidad_series() si aplica

3. Actualiza estado:
   - StockProducto.cantidad (modificable)
   - InventorySnapshot (historico immutable)

4. Emite eventos:
   a) DomainEventService.record_event(
        event_type="INVENTARIO_MOVIMIENTO",
        aggregate_type="MovimientoInventario",
        payload={tipo, bodega, producto, cantidad, trazabilidad...},
        idempotency_key=f"domain:movimiento_{movimiento.id}"
      )

   b) OutboxService.enqueue(
        event_type="INVENTARIO_ACTUALIZADO",
        payload={bodega, producto, cantidad_nueva, cantidad_anterior},
        consumer_name="reservas"  # Consumer que activa/libera reservas
      )

5. Consumer de reservas:
   - ReservaService.actualizar_disponible(producto, bodega, cantidad_nueva)
   - Verifica si hay reservas pendientes que ahora pueden confirmarse
```

Archivos involucrados:
- `apps/inventario/services/inventario_service.py`
- `apps/inventario/models/__init__.py` — StockProducto, MovimientoInventario, InventorySnapshot

### Flujo ejemplo: Contabilizacion de documento de compra

```
1. DocumentoCompraService.registrar_documento(...)
   -> Crea factura/guia de proveedor

2. Emite solicitud al puente contable:
   AccountingBridge.request_entry(
      numero_referencia=f"DOC_COMPRA_{documento.id}",
      tipo_entrada="COMPRA",
      conceptos=[
        {cuenta: "2101", debe: 1000, descripcion: "Factura XXX de Proveedor YYY"},
        {cuenta: "2105", debe: 100, descripcion: "IVA"},
      ],
      meta={documento_id: documento.id, proveedor_id: ...}
   )

3. AccountingBridge ejecuta internamente:
   - DomainEventService.record_event(
       event_type="SOLICITUD_ASIENTO_CONTABLE",
       payload={conceptos, numero_referencia, ...},
       idempotency_key=f"domain:doc_compra_{documento.id}"
     )
     -> Persiste solicitud funcional

   - OutboxService.enqueue(
       event_type="ASIENTO_CONTABLE_SOLICITADO",
       payload={...conceptos...},
       idempotency_key=f"outbox:doc_compra_{documento.id}",
       consumer_name="contabilidad"  # Modulo de contabilidad (futuro)
     )
     -> Encola para consumer contable

4. CarteraService.registrar_cxp_desde_documento_compra(...)
   -> Crea CxP con referencia a documento
   -> Emite OutboxEvent si es primera vez (dedup por document_id)

5. Cuando integrador contable consume OutboxEvent:
   - Crea asiento en modulo Contabilidad (futuro)
   - Registra liga entre documento_compra <-> asiento_contable
   - Retorna confirmacion en OutboxEvent (mark_sent)
```

Archivos involucrados:
- `apps/compras/services/documento_compra_service.py`
- `apps/core/services/accounting_bridge.py`
- `apps/core/services/cartera_service.py`

## Principios de Idempotencia

Todos los flujos usan `idempotency_key` para garantizar operaciones exactitud-una:

1. **Estratificacion de keys**:
   - `domain:` — Eventos funcionales (trazabilidad interna)
   - `outbox:` — Integraciones (hacia consumidores)
   - Permiten reutilizar mismo numero de referencia sin conflictos.

2. **Deduplicacion en servicios**:
   - `DomainEventService`: `get_or_create(idempotency_key=key)` retorna evento existente.
   - `OutboxService`: idem, evita encolados duplicados.
   - `CarteraService`: `update_or_create(referencia_estable)` evita multiples CxP/CxC.

3. **Reintentos seguros**:
   - ViewSet llama `SecuenciaService.obtener_siguiente_numero()` con retry loop.
   - Si transaccion falla (timeout, conflicto), siguiente intento usa mismo idempotency_key.
   - Servicios devuelven resultado existente sin duplicar.

## Modelo de negocio base (resumen)

## Modelo de negocio base (resumen)

### Multi-tenant automatico
- Cada modelo operativo hereda de `BaseModel` (`apps/core/models/base.py`).
- `BaseModel.save()` auto-asigna `empresa` desde contexto (`ContextVar` set por middleware).
- Dos managers:
  - `objects` (default): Filtra automaticamente por empresa actual (evita acceso cross-tenant).
  - `all_objects`: Acceso sin filtro (solo servicios internos/async que explicitly necesitan).
- Middleware `EmpresaMiddleware` injeta empresa en `ContextVar` antes de cada request; la limpia tras respuesta.

Flujo:
```
Request entra
  -> EmpresaMiddleware.set_current_empresa(user.empresa_activa)
  -> ViewSet.get_queryset() usa manager default (filtra por empresa)
  -> Modelos.objects.filter(...) garantiza aislamiento de datos
  -> Respuesta retorna
  -> Middleware limpia ContextVar
```

### Validacion automatica en guardado
- `BaseModel.save()` ejecuta `full_clean()` antes de persistir (mapea a `ValidationError` de formularios).
- Excepto si se pasa `skip_clean=True` (usar solo en admin).
- Permite atrapar errores de negocio tempranamente sin excepciones de BD.

Modelos obligatorios en `BaseModel`:
- `id` (UUID v4, PK)
- `empresa` (FK a Empresa, asignado automaticamente)
- `creado_en`, `actualizado_en` (auto)
- `creado_por` (FK a User, asignado automaticamente)

### Documentos y folios
- Las secuencias por empresa se gestionan en `SecuenciaService` (atomicas con `select_for_update()`).
- Cada documento (presupuesto, orden compra, factura) obtiene folio unico reservando en transaccion.
- Formato configurable: `{prefijo}{numero_paddeado}` (ej. "SOM-000001", "FAC-000042").
- Reintentos: ViewSet reintenta si timeout (DRF + Django ORM manejan locks).
- No hay "gaps" deliberados (todos los numeros son secuenciales) a menos que haya cancelacion.

### Inventario (Trazabilidad + Multibodega)
- Stock valorizado por `bodega` (multiples ubicaciones).
- `StockProducto`: cantidad por bodega, costo promedio ponderado, actualizado en cada movimiento.
- `InventorySnapshot`: historico immutable de cada movimiento (FIFO/LIFO/promedio).
- Trazabilidad opcional por producto:
  - **Por lote**: `StockLote` con numero_lote, fecha_vencimiento, cantidad.
  - **Por serie**: `StockSerie` con numero_serie, estado (NUEVO, USADO, DEFECTUOSO, etc.).
  - **Reservas de stock**: `ReservaStock` vincula presupuestos/ordenes con stock disponible (evita sobreventa).

Flujo de movimiento:
```
InventarioService.registrar_movimiento(producto, bodega, cantidad, tipo, trazabilidad={})
  1. Valida reglas (cantidad > 0, bodega existe, etc.)
  2. Si tipo=ENTRADA: aumenta stock
  3. Si tipo=SALIDA: valida disponible >= cantidad
  4. Si trazabilidad.lotes: registra en StockLote + InventorySnapshot
  5. Si trazabilidad.series: registra en StockSerie + InventorySnapshot
  6. Emite DomainEvent + OutboxEvent
```

### Auditoria con hash chain (Append-only immutable)
- Modelo `AuditEvent` en `apps/auditoria/models.py`.
- Campos: `module_code` (PRESUPUESTOS, COMPRAS, etc.), `action_code` (CREAR, APROBAR, etc.), `entity_type`, `entity_id`, `summary`, `changes`, `event_hash`, `previous_hash`.
- **Hash chain**: `event_hash` depende de contenido + `previous_hash` (blockchain-like).
- Deduplicacion: `idempotency_key` evita duplicados si se reintenta misma auditoria.
- Indices compuestos: `(empresa, module_code, occurred_at)` y `(empresa, entity_type, entity_id, occurred_at)` para queries rapidas.

### Seguridad
- Auth JWT via cookies `HttpOnly` (impermeables a XSS).
- CSRF reforzado en unsafe methods (POST, PUT, DELETE).
- Permisos por modulo/accion y empresa: `TienePermisoModuloAccion` valida contra `permission_action_map` en ViewSet.
- Roles: OWNER, ADMIN, VENDEDOR, CONTADOR (extensible).
- UserEmpresa.activo controla acceso multi-empresa (una persona puede tener multiples roles en multiples empresas).

### Excepciones de dominio (Clean layers)
- Servicios lanzan solo `AppError` subclases: `BusinessRuleError` (400), `AuthorizationError` (403), `ResourceNotFoundError` (404), `ConflictError` (409).
- NO importan `rest_framework.exceptions` ni `django.core.exceptions.ValidationError` en `apps/**/services/*.py`.
- Capa API: ViewSet.create()/update() valida con serializer, luego llama servicio; excepciones se propagan al handler global.
- Global handler (`apps/core/api/exception_handler.py`) convierte `AppError` a JSON `{detail, error_code, meta?}`.

Ejemplo:
```python
# En PresupuestoService (negocio)
if not presupuesto.items.exists():
    raise BusinessRuleError("No se puede aprobar sin items.")  # No sabe de HTTP

# En exception_handler (API)
if isinstance(exc, AppError):
    return Response(
        data={"detail": exc.detail, "error_code": exc.error_code, "meta": exc.meta},
        status=exc.status_code
    )
```

## Estandar para nuevos modulos

Para un modulo nuevo (`ventas`, `tesoreria`, `contabilidad`), seguir este checklist:

### 1. Estructura base
```
apps/nuevo_modulo/
  __init__.py
  admin.py
  apps.py (AppConfig)
  models/
    __init__.py          # Importa y expone todos modelos
    entidad_principal.py # Hereda BaseModel
    entidad_relacion.py
    entidades_historico.py   # Si auditoria/eventos internos
  services/
    __init__.py          # Importa servicios
    servicio_principal.py     # Logica de negocio
    servicio_auxiliar.py
  api/
    __init__.py
    serializers.py       # DRF serializers
    views.py             # ViewSets con permission_action_map
    filters.py (opcional)
  tests/
    __init__.py
    test_models.py
    test_services.py     # Tests unitarios (sin DB)
    test_api.py          # Tests de viewsets (con DB)
    test_eventos.py      # Tests de DomainEvent/OutboxEvent
  permisos.py (opcional)   # Constantes de permisos si modulo define nuevos
```

### 2. Modelos
- Todos heredan de `BaseModel` para auto-multitenancy.
- Definir entidad principal con estados (ej. `Venta.estado` can "BORRADOR", "CONFIRMADA", etc.).
- Si tiene items (lineas): crear model relacion con FK + UUID explícito.
- Si necesita historico: crear model historico immutable para auditar cambios.

Ejemplo:
```python
# apps/ventas/models/venta.py
from apps.core.models import BaseModel

class Venta(BaseModel):
    ESTADOS = [("BORRADOR", "Borrador"), ("CONFIRMADA", "Confirmada"), ...]
    numero_folio = CharField(max_length=20, unique_for_date="creado_en")
    estado = CharField(max_length=20, choices=ESTADOS, default="BORRADOR")
    cliente = ForeignKey("contactos.Cliente", on_delete=CASCADE)
    fecha = DateField()
    total = DecimalField(max_digits=15, decimal_places=2)
    
    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["empresa", "estado", "creado_en"]),
            models.Index(fields=["empresa", "cliente", "estado"]),
        ]
```

### 3. Servicios
- Centralizar todas reglas en `apps/nuevo_modulo/services/servicio_principal.py`.
- Metodos levanten solo `AppError` subclases (BusinessRuleError, etc.).
- NO importar `rest_framework.exceptions`.
- Cada metodo incluir docstring breve en espanol tecnico (ver seccion "Documentacion").
- Usar `@transaction.atomic` si multiples updates/creates.

Ejemplo:
```python
# apps/ventas/services/venta_service.py
from apps.core.exceptions import BusinessRuleError, ResourceNotFoundError
from apps.core.services import WorkflowService, DomainEventService, OutboxService

class VentaService:
    """Logica de negocio para gestionar ventas."""
    
    ESTADOS_TRANSICION = {
        "BORRADOR": ["CONFIRMADA", "CANCELADA"],
        "CONFIRMADA": ["ENVIADA", "CANCELADA"],
        "ENVIADA": ["ENTREGADA", "DEVUELTA"],
        "ENTREGADA": [],
        "CANCELADA": [],
    }
    
    @transaction.atomic
    def crear_venta(self, empresa, cliente, items_data, usuario=None):
        """
        Crea venta en estado BORRADOR.
        
        Valida:
        - Cliente existe y activo
        - Items no vacío
        - Stock disponible si manejo_inventario activado
        
        Emite: DomainEvent, OutboxEvent
        """
        if not cliente.activo:
            raise BusinessRuleError("Cliente debe estar activo.")
        
        if not items_data:
            raise BusinessRuleError("Venta debe tener al menos un item.")
        
        # Reservar stock si aplica
        for item_data in items_data:
            producto = Producto.objects.get(id=item_data["producto_id"])
            InventarioService.validar_stock_disponible(
                empresa=empresa,
                producto=producto,
                cantidad=item_data["cantidad"]
            )
        
        venta = Venta.objects.create(
            empresa=empresa,
            cliente=cliente,
            estado="BORRADOR",
            creado_por=usuario
        )
        
        # Crear items
        for item_data in items_data:
            VentaItem.objects.create(
                venta=venta,
                producto_id=item_data["producto_id"],
                cantidad=item_data["cantidad"],
                precio_unitario=item_data["precio_unitario"]
            )
        
        # Emitir eventos
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="Venta",
            aggregate_id=venta.id,
            event_type="VENTA_CREADA",
            payload={"venta_id": str(venta.id), "cliente_id": str(cliente.id)},
            usuario=usuario,
            idempotency_key=f"domain:venta_{venta.id}_creada"
        )
        
        return venta
    
    @transaction.atomic
    def confirmar_venta(self, empresa, venta_id, usuario=None):
        """
        Confirma venta: BORRADOR -> CONFIRMADA.
        
        Valida:
        - Venta existe
        - Transicion valida
        - Stock sigue disponible
        
        Emite eventos de dominio + integracion (ej. generacion de factura).
        """
        venta = Venta.objects.get(id=venta_id, empresa=empresa)
        
        # Validar transicion
        next_state = WorkflowService.assert_transition(
            venta.estado,
            "CONFIRMADA",
            self.ESTADOS_TRANSICION
        )
        
        # Reservar stock atomicamente
        for item in venta.items.all():
            InventarioService.reservar_stock(
                empresa=empresa,
                producto=item.producto,
                cantidad=item.cantidad,
                documento_ref=venta.id
            )
        
        # Aplicar transicion
        venta = WorkflowService.apply_transition(
            venta,
            next_state,
            self.ESTADOS_TRANSICION
        )
        
        # Emitir eventos
        DomainEventService.record_event(...)
        OutboxService.enqueue(...)
        
        # Solicitar factura a puente contable
        AccountingBridge.request_entry(...)
        
        return venta
```

### 4. API (ViewSets)
- Heredar de `TenantViewSetMixin` + `ModelViewSet`.
- Definir `permission_modulo` y `permission_action_map` para validacion de permisos.
- Acciones personalizadas usar `@action` decorator.
- Serializers validan input; servicios lanzan excepciones; handler convierte a HTTP.

Ejemplo:
```python
# apps/ventas/api/views.py
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.mixins import TenantViewSetMixin
from apps.core.permisos.constantes_permisos import Modulos, Acciones

class VentaViewSet(TenantViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    serializer_class = VentaSerializer
    filterset_class = VentaFilter
    permission_modulo = Modulos.VENTAS
    permission_action_map = {
        "list": Acciones.VER,
        "retrieve": Acciones.VER,
        "create": Acciones.CREAR,
        "update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,
        "confirmar": Acciones.CONFIRMAR,  # Accion personalizada
    }
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        venta = VentaService.crear_venta(
            empresa=self.get_empresa(),
            cliente_id=serializer.validated_data["cliente"].id,
            items_data=serializer.validated_data["items"],
            usuario=request.user
        )  # Si levanta AppError -> exception_handler convierte
        
        return Response(
            VentaSerializer(venta).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        venta = self.get_object()
        venta = VentaService.confirmar_venta(
            empresa=self.get_empresa(),
            venta_id=venta.id,
            usuario=request.user
        )
        
        return Response(VentaSerializer(venta).data)
```

### 5. Eventos de dominio + Integraciones
- `DomainEventService.record_event()` en cada flujo principal (crear, cambiar estado, etc.).
- `OutboxService.enqueue()` para eventos que consumidores externos necesitan.
- Usar `idempotency_key` estratificado: `domain:` y `outbox:`.

### 6. Auditoria (si aplica)
- Heredar de `AuditoriaMixin` en ViewSet para auto-registrar cambios.
- O llamar `AuditoriaService.registrar_evento()` manualmente.

Ejemplo:
```python
class VentaViewSet(AuditoriaMixin, ...):
    audit_module = "VENTAS"
    
    def perform_update(self, serializer):
        # AuditoriaMixin auto-registra cambios
        super().perform_update(serializer)
```

### 7. Tests
- Unitarios: Mock BD, testear logica servicio con casos normales + excepciones.
- API: Usar cliente HTTP, validar status codes + estructuras respuesta.
- Eventos: Validar que DomainEvent + OutboxEvent se crean correctamente.

Ejemplo:
```python
# apps/ventas/tests/test_services.py
import pytest
from apps.ventas.services import VentaService
from apps.core.exceptions import BusinessRuleError

@pytest.mark.django_db
def test_crear_venta_sin_items():
    empresa = Empresa.objects.create(nombre="Test")
    cliente = Cliente.objects.create(empresa=empresa, nombre="Test")
    
    with pytest.raises(BusinessRuleError, match="debe tener al menos un item"):
        VentaService.crear_venta(empresa, cliente, [])

# apps/ventas/tests/test_api.py
@pytest.mark.django_db
def test_crear_venta_api(client, usuario, empresa):
    set_current_empresa(empresa)
    
    response = client.post(
        "/api/ventas/",
        {"cliente_id": "...", "items": [...]},
        content_type="application/json"
    )
    
    assert response.status_code == 201
    assert "id" in response.data
```

### 8. Documentacion
- Crear `apps/nuevo_modulo/README.md` con arquitectura local (si complejo).
- Documentar permisos, estados, flujos principales.
- Agregar docstrings en espanol tecnico en servicios (ver "Convenciones" abajo).

## Convenciones de documentacion tecnica
- Todo metodo nuevo en `apps/**/services/*.py` debe incluir docstring breve en espanol tecnico.
- Si existe logica no obvia (idempotencia, concurrencia, locks, tolerancias), agregar comentario corto en espanol.
- Evitar comentarios redundantes.

## Publicacion en GitHub Pages
Sugerencia:
- Exponer `docs/` dentro del sitio de documentacion.
- Mantener esta pagina como indice tecnico de arquitectura.
- Crear paginas por modulo (`ventas.md`, `tesoreria.md`, `contabilidad.md`) usando esta estructura.
