# Guia Practica de Desarrollo

## Configuracion inicial

### Base de datos
```bash
# Migraciones pendientes
python manage.py migrate

# Crear superuser
python manage.py createsuperuser

# Ver estado migraciones
python manage.py showmigrations
```

### Base de datos (shell)
```bash
# Django shell para queries interactivas
python manage.py shell

# En shell:
from apps.presupuestos.models import Presupuesto
from apps.core.tenant import set_current_empresa
from apps.contactos.models import Empresa

# Set tenant context
empresa = Empresa.objects.first()
set_current_empresa(empresa)

# Query normal (filtra auto por empresa)
presupuestos = Presupuesto.objects.all()

# Query sin filtro (admin only)
presupuestos_todas = Presupuesto.all_objects.all()
```

## Testing

### Correr tests
```bash
# Todos los tests
pytest

# Tests de un modulo
pytest apps/presupuestos/tests/

# Tests de un archivo
pytest apps/presupuestos/tests/test_services.py

# Test especifico
pytest apps/presupuestos/tests/test_services.py::test_crear_presupuesto

# Con verbose
pytest -v

# Con stdout
pytest -s

# Con cobertura
pytest --cov=apps --cov-report=html
```

### Estructura de tests

**Test de servicio** (unitario, sin BD):
```python
# apps/presupuestos/tests/test_services.py
import pytest
from apps.presupuestos.services import PresupuestoService
from apps.core.exceptions import BusinessRuleError

@pytest.mark.django_db
def test_crear_presupuesto_sin_items():
    empresa = Empresa.objects.create(nombre="Test")
    cliente = Cliente.objects.create(empresa=empresa, nombre="Test")
    
    with pytest.raises(BusinessRuleError, match="debe tener"):
        PresupuestoService.crear_presupuesto(
            empresa=empresa,
            cliente=cliente,
            items_data=[]
        )
```

**Test de API** (con cliente HTTP):
```python
# apps/presupuestos/tests/test_api.py
import pytest
from django.test import Client

@pytest.mark.django_db
def test_crear_presupuesto_api(client, usuario, empresa):
    # client es DRF test client
    response = client.post(
        "/api/presupuestos/",
        {"cliente_id": "...", "items": [...]},
        content_type="application/json"
    )
    
    assert response.status_code == 201
    assert "id" in response.data
    assert response.data["estado"] == "BORRADOR"

@pytest.mark.django_db
def test_crear_presupuesto_sin_permiso(client, usuario_vendedor):
    # usuario_vendedor NO tiene permiso CREAR en PRESUPUESTOS
    response = client.post("/api/presupuestos/", {...})
    
    assert response.status_code == 403
    assert response.data["error_code"] == "PERMISSION_DENIED"
```

### Fixtures

**Ubicacion**: `conftest.py` (raiz backend/ y por modulo)

```python
# backend/conftest.py
import pytest
from django.contrib.auth import get_user_model
from apps.contactos.models import Empresa, UserEmpresa
from apps.core.tenant import set_current_empresa

User = get_user_model()

@pytest.fixture
def empresa():
    return Empresa.objects.create(nombre="Test Corp")

@pytest.fixture
def usuario(empresa):
    user = User.objects.create_user(
        username="test@test.com",
        password="testpass123",
        empresa_activa=empresa
    )
    UserEmpresa.objects.create(
        usuario=user,
        empresa=empresa,
        rol="ADMIN",
        activo=True
    )
    return user

@pytest.fixture
def usuario_vendedor(empresa):
    user = User.objects.create_user(
        username="vendedor@test.com",
        password="testpass123",
        empresa_activa=empresa
    )
    UserEmpresa.objects.create(
        usuario=user,
        empresa=empresa,
        rol="VENDEDOR",
        activo=True
    )
    return user

@pytest.fixture
def client(usuario):
    from django.test import Client
    client = Client()
    # Login via API o set auth header
    set_current_empresa(usuario.empresa_activa)
    return client
```

## Monitoreo y Debugging

### Logs

**Ubicacion**: `apps/**/services/*.py`

```python
import logging

logger = logging.getLogger(__name__)

def crear_presupuesto(...):
    logger.info(
        "presupuesto_crear_iniciado",
        extra={
            "cliente_id": cliente.id,
            "empresa_id": empresa.id,
            "items_count": len(items_data),
        }
    )
    
    try:
        # ... logica ...
        logger.info("presupuesto_creado", extra={"presupuesto_id": presupuesto.id})
    except Exception as e:
        logger.error(
            "presupuesto_crear_error",
            exc_info=True,
            extra={"error": str(e)}
        )
        raise
```

**Ver logs en desarrollo**:
```bash
# Con runserver
python manage.py runserver --debug-sql

# Ver SQL en shell
from django.conf import settings
settings.DEBUG = True

from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as ctx:
    presupuestos = Presupuesto.objects.all()

for query in ctx:
    print(query["sql"])
```

### Eventos de dominio

**Validar que se registran**:
```python
from apps.core.models import DomainEvent

# Luego de crear presupuesto
evento = DomainEvent.objects.filter(
    tipo_evento="PRESUPUESTO_CREADO",
    agregado_id=presupuesto.id
).first()

assert evento is not None
assert evento.payload["cliente_id"] == str(cliente.id)
```

**Validar Outbox**:
```python
from apps.core.models import OutboxEvent

# Luego de aprobar
outbox = OutboxEvent.objects.filter(
    tipo_evento="PRESUPUESTO_APROBADO",
    status="PENDING"  # O "SENT" si consumer ya proceso
).first()

assert outbox is not None
```

### Auditoria

**Ver eventos de auditoria**:
```python
from apps.auditoria.models import AuditEvent

# Cambios a presupuesto especifico
eventos = AuditEvent.objects.filter(
    entity_type="Presupuesto",
    entity_id=presupuesto.id
).order_by("occurred_at")

for evento in eventos:
    print(f"{evento.action_code}: {evento.summary}")
    print(f"  Cambios: {evento.changes}")
    print(f"  Usuario: {evento.usuario.username}")
    print(f"  Hash: {evento.event_hash}")
```

## Comandos Django utiles

### Management commands

**Ver apps disponibles**:
```bash
python manage.py startapp nombre
```

**Cargar datos iniciales** (fixtures):
```bash
# Crear fixture
python manage.py dumpdata apps.contactos > fixture_contactos.json

# Cargar fixture
python manage.py loaddata fixture_contactos.json
```

**Ver modelos**:
```bash
python manage.py inspect_db
```

## Queries comunes

### Multi-tenant

```python
from apps.core.tenant import set_current_empresa, get_current_empresa

# En ViewSet o servicio
set_current_empresa(usuario.empresa_activa)

# Queries filtran auto
presupuestos = Presupuesto.objects.all()  # Solo empresa actual

# Sin filtro (admin)
presupuestos_todas = Presupuesto.all_objects.all()

# O filter manual
presupuestos = Presupuesto.objects.filter(empresa=empresa)
```

### Filtros comunes

```python
from django.db.models import Q, F, Sum
from django.utils import timezone

# Presupuestos pendientes de aprobacion
pendientes = Presupuesto.objects.filter(estado="ENVIADO")

# Presupuestos vencidos (creado hace > 30 dias)
from datetime import timedelta
vencidos = Presupuesto.objects.filter(
    creado_en__lt=timezone.now() - timedelta(days=30),
    estado__in=["BORRADOR", "ENVIADO"]
)

# Por cliente
presupuestos_cliente = Presupuesto.objects.filter(cliente=cliente)

# Multiples condiciones
presupuestos = Presupuesto.objects.filter(
    Q(estado="APROBADO") | Q(estado="ENVIADO"),
    cliente__activo=True
)

# Agregaciones
totales = Presupuesto.objects.filter(
    estado="APROBADO"
).aggregate(total=Sum("monto_total"))
```

### Actualizaciones atomicas

**IMPORTANTE: Usar @transaction.atomic en servicios**

```python
from django.db import transaction

@transaction.atomic
def aprobar_presupuesto(presupuesto):
    # Valida
    if not presupuesto.items.exists():
        raise BusinessRuleError("Sin items")
    
    # Actualiza
    presupuesto.estado = "APROBADO"
    presupuesto.save()
    
    # Emite eventos
    DomainEventService.record_event(...)
    OutboxService.enqueue(...)
    
    # Si algo falla en eventos, se revierte TODO
```

## Permisos y testing

### Asignar permisos para test

```python
from apps.core.models import PermisoUsuario
from apps.core.permisos.constantes_permisos import Modulos, Acciones

# Dar permiso CREATE a usuario
PermisoUsuario.objects.create(
    usuario=usuario,
    empresa=empresa,
    modulo=Modulos.PRESUPUESTOS,
    accion=Acciones.CREAR,
    rol="VENDEDOR"
)

# Validar que tiene permiso
assert usuario.tiene_permiso(
    Modulos.PRESUPUESTOS,
    Acciones.CREAR,
    empresa
) == True
```

## Versionamiento de API

### Cambios backwards-compatible

1. **Agregar campos opcionales**: OK, clientes ignoraran si no soportan.
2. **Deprecar campos**: Mantener en respuesta pero marcar como deprecated en docs.
3. **Eliminar campos**: Nunca en misma version; requerir version bump.

### Cambios NO backwards-compatible

```python
# Cambiarelectricity Cambiar structure de respuesta
# Inicialmente (v1)
{"id": "...", "nombre": "..."}

# Despues (v2) - ROMPE clientes v1
{"id": "...", "nombre": "...", "apellido": "..."}  # Campo agregado
{"id": "...", "rut": "..."}  # Campo removido/renombrado - ROMPE

# Solucion: Version API
# URLs:
# /api/v1/presupuestos/  # Respuesta vieja
# /api/v2/presupuestos/  # Respuesta nueva con cambios
```

## Performance

### N+1 queries

**Problema**:
```python
presupuestos = Presupuesto.objects.all()
for presupuesto in presupuestos:
    print(presupuesto.cliente.nombre)  # N queries extras!
```

**Solucion**:
```python
presupuestos = Presupuesto.objects.select_related("cliente")
for presupuesto in presupuestos:
    print(presupuesto.cliente.nombre)  # 0 queries extras
```

**Con items** (reverse FK):
```python
dari MALO:
presupuestos = Presupuesto.objects.all()
for presupuesto in presupuestos:
    items = presupuesto.items.all()  # N queries

# BUENO:
presupuestos = Presupuesto.objects.prefetch_related("items")
for presupuesto in presupuestos:
    items = presupuesto.items.all()  # Cache
```

### Indices

Ver indexes en modelos:
```python
class Presupuesto(BaseModel):
    estado = CharField(...)
    cliente = ForeignKey(...)
    
    class Meta:
        indexes = [
            models.Index(fields=["empresa", "estado", "creado_en"]),
            models.Index(fields=["cliente", "creado_en"]),
        ]
```

Crear migracion si agregaste indice:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Debugging de permissions

### Ver permisos del usuario

```python
# En shell o test
usuario = User.objects.get(username="test")
empresa = Empresa.objects.first()

# Ver relaciones
relaciones = UserEmpresa.objects.filter(usuario=usuario)
for rel in relaciones:
    print(f"Rol: {rel.rol}, Empresa: {rel.empresa.nombre}, Activo: {rel.activo}")

# Ver permisos individuales
permisos = PermisoUsuario.objects.filter(
    usuario=usuario,
    empresa=empresa
)
for perm in permisos:
    print(f"{perm.modulo} - {perm.accion}")

# Validar permiso
tiene_permiso = usuario.tiene_permiso(
    Modulos.PRESUPUESTOS,
    Acciones.CREAR,
    empresa
)
print(f"Tiene CREATE en PRESUPUESTOS: {tiene_permiso}")
```

### Debuguear 403 Forbidden

```python
# En test que lance 403
response = client.post(...)
assert response.status_code == 403

# Ver detalles
print(response.data)
# {"detail": "...", "error_code": "PERMISSION_DENIED", ...}

# Rastrear cual permission fallo
# 1. IsAuthenticated?
# 2. TieneRelacionActiva?
# 3. TienePermisoModuloAccion?

# Checar cada una manualmente
print(f"Autenticado: {usuario.is_authenticated}")
print(f"Relacion activa: {UserEmpresa.objects.filter(usuario=usuario, empresa=empresa, activo=True).exists()}")
print(f"Tiene permiso: {usuario.tiene_permiso(modulo, accion, empresa)}")
```
