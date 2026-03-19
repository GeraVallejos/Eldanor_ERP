# Auditoria y Trazabilidad

## Vision general

El sistema tiene **dos capas de trazabilidad** que funcionan juntas:

1. **Auditoria funcional** (`DomainEventService`): Eventos de negocio append-only.
2. **Auditoria operacional** (`AuditEvent`): Cambios a entidades con hash chain.

Ambas son **immutable** y **append-only** para cumplir compliance.

## Capa 1: Domain Events (Negocio)

**Ubicacion**: `apps/core/services/domain_event_service.py` + `apps/core/models/domain_event.py`

**Responsabilidad**: Registrar **eventos funcionales** de negocio (PRESUPUESTO_CREADO, PRESUPUESTO_APROBADO, INVENTARIO_MOVIMIENTO, etc.).

### Metodo principal

```python
DomainEventService.record_event(
    empresa,                  # Empresa propietaria
    aggregate_type,           # "Presupuesto", "Inventario", "Documento", etc.
    aggregate_id,             # UUID de entidad principal
    event_type,               # "PRESUPUESTO_APROBADO", etc.
    payload,                  # Dict con datos del evento
    meta=None,                # Dict adicional (opcional)
    idempotency_key=None,     # Para dedup
    usuario=None,             # Usuario que causo evento
    event_version=1           # Version del schema evento (extensible)
)
```

### Modelo DomainEvent

```python
class DomainEvent(BaseModel):
    agregado_tipo = CharField(max_length=100)      # "Presupuesto"
    agregado_id = UUIDField()                       # ID entidad
    tipo_evento = CharField(max_length=100)        # "PRESUPUESTO_APROBADO"
    payload = JSONField()                           # Datos del evento
    meta = JSONField(null=True, blank=True)        # Contexto adicional
    idempotency_key = CharField(max_length=255, unique_for_empresa=True)  # Dedup
    usuario = ForeignKey(User, null=True)          # Quien causo cambio
    evento_version = IntegerField(default=1)       # Schema version
    
    class Meta:
        ordering = ["creado_en"]           # Append-only: siempre cronologico
        indexes = [
            Index(fields=["empresa", "agregado_tipo", "agregado_id", "creado_en"]),
            Index(fields=["empresa", "tipo_evento", "creado_en"]),
            Index(fields=["idempotency_key"]),
        ]
    
    def __str__(self):
        return f"{self.tipo_evento} on {self.agregado_tipo}#{self.agregado_id}"
```

### Ejemplo de uso

```python
# En PresupuestoService.aprobar_presupuesto()

@transaction.atomic
def aprobar_presupuesto(presupuesto, usuario):
    # ... logica de negocio ...
    presupuesto.estado = "APROBADO"
    presupuesto.save()
    
    # Registrar evento funcional
    DomainEventService.record_event(
        empresa=presupuesto.empresa,
        aggregate_type="Presupuesto",
        aggregate_id=presupuesto.id,
        event_type="PRESUPUESTO_APROBADO",
        payload={
            "presupuesto_id": str(presupuesto.id),
            "numero_folio": presupuesto.numero_folio,
            "cliente_id": str(presupuesto.cliente_id),
            "monto_total": str(presupuesto.monto_total),
            "aprobado_por": usuario.username,
        },
        usuario=usuario,
        idempotency_key=f"domain:presupuesto_{presupuesto.id}_aprobado"  # Unique
    )
    
    # Tambien encolar para integraciones
    OutboxService.enqueue(
        event_type="PRESUPUESTO_APROBADO",
        payload={...},
        idempotency_key=f"outbox:presupuesto_{presupuesto.id}_notificacion",
        consumer_name="notificaciones"
    )
```

### Caracteristicas

- **Append-only**: Nunca se modifica o borra un evento.
- **Deduplicacion**: `idempotency_key` evita duplicados si se reintenta operacion.
- **Trazabilidad**: `usuario` registra quien causo cambio; `creado_en` timestamp inmutable.
- **Extensible**: `evento_version` permite evolucionar schema sin romper compatibilidad.

## Capa 2: Audit Events (Operacional)

**Ubicacion**: `apps/auditoria/models.py` + `apps/auditoria/services/auditoria_service.py`

**Responsabilidad**: Registrar cambios **granulares** a entidades (campos modificados, antes/despues).

### Modelo AuditEvent

```python
class AuditEvent(BaseModel):
    # Clasificacion
    module_code = CharField(max_length=50)         # "PRESUPUESTOS", "COMPRAS"
    action_code = CharField(max_length=50)         # "CREAR", "EDITAR", "APROBAR"
    event_type = CharField(max_length=100)         # "PRESUPUESTO_CREADO", "PRESUPUESTO_ESTADO_CAMBIO"
    
    # Entidad afectada
    entity_type = CharField(max_length=100)        # "Presupuesto"
    entity_id = UUIDField()                         # ID entidad
    
    # Contenido del evento
    summary = TextField()                           # Descripcion legible: "Aprobado presupuesto SOM-001"
    changes = JSONField()                           # {campo: {old, new}} para auditar cambios
    payload = JSONField(null=True)                  # Datos adicionales del evento
    meta = JSONField(null=True)                     # Contexto (IP, User-Agent, etc.)
    
    # Integridad criptografica
    event_hash = CharField(max_length=64)          # SHA256 de contenido + previous_hash
    previous_hash = CharField(max_length=64, null=True)  # Hash del evento anterior (blockchain-like)
    
    # Deduplicacion
    idempotency_key = CharField(max_length=255, unique_for_empresa=True, null=True)
    
    # Auditoria
    usuario = ForeignKey(User, null=True)
    occurred_at = DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            Index(fields=["empresa", "module_code", "occurred_at"]),
            Index(fields=["empresa", "entity_type", "entity_id", "occurred_at"]),
            Index(fields=["empresa", "action_code", "occurred_at"]),
        ]
```

### Hash chain (Integridad)

**Proposito**: Detectar corrupcio o modificacion no autorizada de registros de auditoria.

**Como funciona**:
1. Cada evento calcula `event_hash = SHA256(contenido + previous_hash)`.
2. Si alguien modifica un evento antiguo, `event_hash` se rompe.
3. Todos los eventos posteriores tambien quedan con hash incorrecto.

**Ejemplo**:
```
Evento 1: event_hash = SHA256("Presupuesto creado" + "") = ABC123
Evento 2: event_hash = SHA256("Presupuesto aprobado" + "ABC123") = DEF456
Evento 3: event_hash = SHA256("Presupuesto anulado" + "DEF456") = GHI789

Si alguien modifica Evento 1:
  -> Evento 1 hash = SHA256("Presupuesto EDITADO" + "") != ABC123 FALLA
  -> Evento 2 previous_hash sigue siendo ABC123 pero Evento 1 es diferente DETECTADO
  -> Cadena rota, auditoria comprometida
```

### Servicio AuditoriaService

**Metodo principal**:
```python
AuditoriaService.registrar_evento(
    empresa,
    module_code,        # "PRESUPUESTOS"
    action_code,        # "CREAR", "EDITAR"
    event_type,         # "PRESUPUESTO_CREADO"
    entity_type,        # "Presupuesto"
    entity_id,          # UUID presupuesto
    summary,            # "Creado presupuesto SOM-001"
    changes=None,       # {"estado": {"old": "BORRADOR", "new": "ENVIADO"}}
    payload=None,       # Datos adicionales
    meta=None,          # {"ip": "192.168.1.1", "user_agent": "..."}
    usuario=None,
    idempotency_key=None,
)
```

### Ejemplo de uso

**Opcion 1: ViewSet con mixin**

```python
class PresupuestoViewSet(AuditoriaMixin, TenantViewSetMixin, ModelViewSet):
    audit_module = "PRESUPUESTOS"
    
    def perform_create(self, serializer):
        presupuesto = serializer.save()
        
        # AuditoriaMixin auto-registra:
        # - action_code = "CREAR"
        # - summary = "Creado presupuesto SOM-001"
        # - entity_id = presupuesto.id
        # - usuario = request.user

    def perform_update(self, serializer):
        old = serializer.instance.__dict__.copy()
        presupuesto = serializer.save()
        new = presupuesto.__dict__.copy()
        
        changes = {}
        for field in ["estado", "monto_total"]:
            if old.get(field) != new.get(field):
                changes[field] = {"old": old[field], "new": new[field]}
        
        # AuditoriaMixin auto-registra cambios:
        # - changes = cambios detectados
```

**Opcion 2: Llamada manual en servicio**

```python
@transaction.atomic
def anular_presupuesto(presupuesto, razon, usuario):
    presupuesto.estado = "ANULADO"
    presupuesto.razon_anulacion = razon
    presupuesto.save()
    
    # Registrar auditoria manual
    AuditoriaService.registrar_evento(
        empresa=presupuesto.empresa,
        module_code="PRESUPUESTOS",
        action_code="ANULAR",
        event_type="PRESUPUESTO_ANULADO",
        entity_type="Presupuesto",
        entity_id=presupuesto.id,
        summary=f"Anulado presupuesto {presupuesto.numero_folio}: {razon}",
        changes={
            "estado": {"old": "APROBADO", "new": "ANULADO"},
            "razon_anulacion": {"old": None, "new": razon},
        },
        payload={"razon": razon},
        usuario=usuario,
        idempotency_key=f"audit:presupuesto_{presupuesto.id}_anular"
    )
```

### Caracteristicas

- **Append-only**: Nunca se modifica o borra un evento.
- **Granular**: Captura cambios de campo (antes/despues).
- **Verificable**: Hash chain detecta tamper.
- **Multidimensional**: Indexa por modulo, accion, entidad para queries rapidas.

## Flujo completo: Aprobacion de presupuesto

```
1. Usuario aprueba presupuesto SOM-001

2. ViewSet.aprobar() llama PresupuestoService.aprobar_presupuesto()
   -> Presupuesto.estado = "APROBADO"
   -> Presupuesto.save()

3. PresupuestoService emite DOMAIN EVENT:
   DomainEventService.record_event(
     event_type="PRESUPUESTO_APROBADO",
     idempotency_key="domain:presupuesto_<id>_aprobado"
   )
   -> Persiste en DomainEvent table (funcional, completo)

4. PresupuestoService tambien encola OUTBOX EVENT:
   OutboxService.enqueue(
     event_type="PRESUPUESTO_APROBADO",
     idempotency_key="outbox:presupuesto_<id>_notificacion"
   )
   -> Persiste en OutboxEvent table (para consumidor asincrono)

5. AuditoriaMixin registra AUDIT EVENT:
   AuditoriaService.registrar_evento(
     module_code="PRESUPUESTOS",
     action_code="APROBAR",
     event_type="PRESUPUESTO_APROBADO",
     changes={"estado": {"old": "ENVIADO", "new": "APROBADO"}},
     idempotency_key="audit:presupuesto_<id>_aprobar"
   )
   -> Persiste en AuditEvent table (granular, con hash chain)

RESULTADO:
- DomainEvent: Registro funcional para negocio/compliance
- OutboxEvent: Encola para notificaciones/integraciones
- AuditEvent: Registro granular con integridad criptografica
```

## Consultas auditoriales

### Tabla de AuditEvents

```python
# Todos cambios a presupuesto XYZ
AuditEvent.objects.filter(
    empresa=empresa,
    entity_type="Presupuesto",
    entity_id=presupuesto_id
).order_by("occurred_at")

# Cambios recientes de modulo PRESUPUESTOS
AuditEvent.objects.filter(
    empresa=empresa,
    module_code="PRESUPUESTOS"
).order_by("-occurred_at")[:100]

# Aprobaciones por usuario
AuditEvent.objects.filter(
    empresa=empresa,
    action_code="APROBAR",
    usuario=usuario
)

# Cambios a campo especifico (JSON query)
from django.db.models import Q
from django.db.models.functions import JSONExtract

AuditEvent.objects.filter(
    empresa=empresa,
    changes__contains={"estado": {"old": "BORRADOR"}}
)
```

### Tabla de DomainEvents

```python
# Historial completo de presupuesto
DomainEvent.objects.filter(
    empresa=empresa,
    agregado_tipo="Presupuesto",
    agregado_id=presupuesto_id
).order_by("creado_en")

# Eventos por tipo
DomainEvent.objects.filter(
    empresa=empresa,
    tipo_evento="PRESUPUESTO_APROBADO"
).order_by("-creado_en")
```

## Notas de compliance

1. **Append-only**: Garantiza no revision de historico (GDPR, compliance).
2. **Deduplicacion**: `idempotency_key` evita registros duplicados si hay fallos.
3. **Usuario**: Cada evento registra quien causo cambio para accountability.
4. **Hash chain**: Detecta tamper no autorizado.
5. **Retention**: Mantener eventos indefinidamente o purgar segun politica de retencion.

## Observabilidad

Logs estructurados (opcional, pero recomendado):
```python
import logging

logger = logging.getLogger("auditoria")

logger.info(
    "presupuesto_aprobado",
    extra={
        "presupuesto_id": presupuesto.id,
        "usuario": usuario.username,
        "empresa": empresa.nombre,
        "monto": presupuesto.monto_total,
    }
)
```

Esto permite:
- Buscar eventos en ELK/Splunk
- Alertas si cambios no autorizados
- Trazabilidad para compliance reports
