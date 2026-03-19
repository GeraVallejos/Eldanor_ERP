# Autenticacion y Permisos

## Autenticacion (JWT + Cookies)

### Flujo de login

```
1. Usuario envia credenciales POST /api/auth/login/
   -> Backend valida contra User.objects.get(username/email)
   -> Genera JWT access + refresh tokens
   -> Retorna tokens en response (data) + HttpOnly cookies

2. Response HTTP:
   - Body: { "access": "eyJ...", "refresh": "eyJ..." }
   - Cookies:
     - Set-Cookie: acceso_token=eyJ...; HttpOnly; Secure; SameSite=Strict
     - Set-Cookie: refresco_token=eyJ...; HttpOnly; Secure; SameSite=Strict

3. Frontend almacena tokens en memory (NO localStorage, evita XSS)
   - O browser auto-maneja cookies HttpOnly transparentemente
```

### Autenticacion en requests

**Clase**: `CookieJWTAuthentication` (`apps/core/authentication.py`)

**Orden de busqueda de JWT**:
1. Header `Authorization: Bearer <token>` (preferido para APIs client-side)
2. Cookie `acceso_token` (usado por browser)

**Metodos**:
```python
def authenticate(self, request):
    # 1. Lee Authorization header
    header = self.get_header(request)
    if header:
        try:
            return super().authenticate(request)  # JWTAuthentication standar
        except AuthenticationFailed:
            pass  # Fallback a cookie

    # 2. Lee cookie acceso_token
    raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_NAME)
    if not raw_token:
        return None  # No autentificado; publico (si DRF lo permite)
    
    # 3. Enforce CSRF en unsafe methods (POST, PUT, DELETE, PATCH)
    if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
        self.enforce_csrf(request)
    
    # 4. Valida JWT
    validated_token = self.get_validated_token(raw_token)
    return (self.get_user(validated_token), validated_token)
```

**CSRF Enforcement**:
- Solo aplica si autenticacion es via cookie (no via header Authorization).
- Valida presencia de X-CSRFToken en headers o CSRF token en form data.
- Evita ataques CSRF donde attacker intenta cambiar estado via form submit.

### Refresh de tokens

```
1. Access token expira (default 15 minutos, configurable)

2. Client envia POST /api/auth/refresh/ con refresh token
   - Via header: Authorization: Bearer <refresh_token>
   - Via cookie: browser auto-envia cookie refresco_token

3. Backend valida refresh token (expira en 7 dias)
   -> Genera nuevo access token
   -> Retorna en cookies + body

4. Importante: Refresh token es long-lived (7 dias)
   -> Almacenar SOLO en cookie HttpOnly
   -> NO exponer en JS (evita robo si XSS)
```

### Logout

```
POST /api/auth/logout/
  -> Backend invalida refresh token (opcional, agrega a blacklist)
  -> Respuesta limpia cookies:
     - Set-Cookie: acceso_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/
     - Set-Cookie: refresco_token=; expires=...
```

## Permisos (Authorization)

### Niveles de permiso

**Nivel 1: Autenticacion**
```python
permission_classes = [IsAuthenticated]
# Valida que request.user.is_authenticated == True
# Rechaza anonimos con 401 Unauthorized
```

**Nivel 2: Relacion empresarial activa**
```python
permission_classes = [IsAuthenticated, TieneRelacionActiva]
# Valida que Usuario tiene UserEmpresa.activo=True para empresa_activa
# Rechaza si relacion inactiva con 403 Forbidden
# Superuser siempre pasa (no necesita UserEmpresa)
```

**Nivel 3: Permiso por modulo/accion**
```python
permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
# Valida que Usuario tiene permiso_modulo + permiso_accion para empresa_activa
# Rechaza con 403 si no tiene permiso
```

### Flujo de autorizacion en ViewSet

```python
class PresupuestoViewSet(TenantViewSetMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, TieneRelacionActiva, TienePermisoModuloAccion]
    
    permission_modulo = Modulos.PRESUPUESTOS  # Modulo
    permission_action_map = {
        "list": Acciones.VER,        # GET /api/presupuestos/ -> accion=VER
        "retrieve": Acciones.VER,    # GET /api/presupuestos/{id}/ -> accion=VER
        "create": Acciones.CREAR,    # POST /api/presupuestos/ -> accion=CREAR
        "update": Acciones.EDITAR,   # PUT /api/presupuestos/{id}/ -> accion=EDITAR
        "partial_update": Acciones.EDITAR,
        "destroy": Acciones.BORRAR,  # DELETE /api/presupuestos/{id}/ -> accion=BORRAR
        "aprobar": Acciones.APROBAR, # POST /api/presupuestos/{id}/aprobar/ -> accion=APROBAR
    }

# Cuando llega GET /api/presupuestos/
# 1. DRF mapea action="list"
# 2. TienePermisoModuloAccion.has_permission() ejecuta:
#    - accion = permission_action_map.get("list") = VER
#    - user.tiene_permiso(modulo=PRESUPUESTOS, accion=VER, empresa=user.empresa_activa)
#    - Si False -> 403 Forbidden
#    - Si True -> ViewSet.list() ejecuta
```

###Constantes de permisos

Ubicacion: `apps/core/permisos/constantes_permisos.py`

```python
class Modulos(str):
    PRESUPUESTOS = "PRESUPUESTOS"
    COMPRAS = "COMPRAS"
    PRODUCTOS = "PRODUCTOS"
    CONTACTOS = "CONTACTOS"
    INVENTARIO = "INVENTARIO"
    AUDITORIA = "AUDITORIA"
    TESORERIA = "TESORERIA"
    CONTABILIDAD = "CONTABILIDAD"
    # ... mas

class Acciones(str):
    VER = "VER"
    CREAR = "CREAR"
    EDITAR = "EDITAR"
    BORRAR = "BORRAR"
    APROBAR = "APROBAR"
    ANULAR = "ANULAR"
    EMITIR = "EMITIR"
    CONFIRMAR = "CONFIRMAR"
    # ... mas

# Catalogo: modulo -> acciones permitidas
PERMISOS_CATALOGO = {
    Modulos.PRESUPUESTOS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.APROBAR,
        Acciones.ANULAR,
        Acciones.BORRAR,
    ],
    Modulos.COMPRAS: [
        Acciones.VER,
        Acciones.CREAR,
        # ...
    ],
    # ...
}
```

### Roles y asignacion

Ubicacion: `apps/core/roles.py` y `apps/core/models/permission_model.py`

**Roles disponibles**:
```python
class RolUsuario(models.TextChoices):
    OWNER = "OWNER"         # Propietario, permisos total
    ADMIN = "ADMIN"         # Administrador, permisos completos por default
    VENDEDOR = "VENDEDOR"   # Vendedor, acceso limitado
    CONTADOR = "CONTADOR"   # Contador, acceso a modulos contables
    # ... extensible
```

**Asignacion de permisos**:
- Modelo `PermisoUsuario(empresa, usuario, modulo, accion, rol)`.
- Cuando usuario crea cuenta en empresa: asignacion de permisos por rol default.
- Admin puede customizar permisos por usuario/rol.

**Logica de validacion**:
```python
# En User.tiene_permiso(modulo, accion, empresa)
# 1. Si user.is_superuser -> True (acceso total)
# 2. Si user.is_staff -> True (deprecated; preferir ADMIN role)
# 3. Revisar PermisoUsuario(empresa, usuario, modulo, accion)
#    -> Si existe -> True
#    -> Si no existe -> False
```

Ejemplo:
```python
usuario = User.objects.get(username="juan")
empresa = Empresa.objects.get(nombre="ACME")

# Juan intenta acceder a presupuestos
usuario.tiene_permiso(
    modulo=Modulos.PRESUPUESTOS,
    accion=Acciones.CREAR,
    empresa=empresa
)
# Busca: PermisoUsuario(usuario=juan, empresa=ACME, modulo=PRESUPUESTOS, accion=CREAR)
# Si existe -> True; Si no -> False
```

## Multi-tenant dentro de misma BD

### Contexto de empresa (Middleware)

**Clase**: `EmpresaMiddleware` (`apps/core/middleware.py`)

Inyecta empresa activa en cada request:

```python
class EmpresaMiddleware:
    def __call__(self, request):
        if request.user.is_authenticated:
            # Resuelove empresa activa
            usuario = request.user
            
            if usuario.is_superuser:
                empresa = usuario.empresa_activa
            else:
                # Obtiene relacion UserEmpresa activa
                relacion = UserEmpresa.objects.filter(
                    usuario=usuario,
                    empresa=usuario.empresa_activa,
                    activo=True
                ).first()
                
                # Fallback a primera relacion activa
                if not relacion:
                    relacion = UserEmpresa.objects.filter(
                        usuario=usuario,
                        activo=True
                    ).first()
                
                empresa = relacion.empresa if relacion else None
            
            # Set contexto para servicio/BD
            set_current_empresa(empresa)
            set_current_user(usuario)
        
        response = self.get_response(request)
        
        # Limpia contexto
        set_current_empresa(None)
        set_current_user(None)
        return response
```

**ContextVar**: `apps/core/tenant.py`
```python
from contextvars import ContextVar

_current_empresa = ContextVar("current_empresa", default=None)
_current_user = ContextVar("current_user", default=None)

def get_current_empresa():
    return _current_empresa.get()

def set_current_empresa(empresa):
    return _current_empresa.set(empresa)
```

### Managers filtrados

**Ubicacion**: `apps/core/models/managers.py`

**EmpresaManager** (default en BaseModel):
```python
class EmpresaManager(models.Manager):
    def get_queryset(self):
        empresa = get_current_empresa()
        qs = super().get_queryset()
        if empresa:
            qs = qs.filter(empresa=empresa)
        return qs
```

**AllObjectsManager** (acceso sin filtro):
```python
class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()  # Sin filtro
```

**Uso**:
```python
# En ViewSet
Presupuesto.objects.all()       # Filtra auto por empresa actual
Presupuesto.all_objects.all()   # Todo (usar solo en admin/batch)

# BaseModel expone ambos
class MyModel(BaseModel):
    objects = EmpresaManager()   # default, filtra
    all_objects = AllObjectsManager()
```

###TenantViewSetMixin

**Ubicacion**: `apps/core/mixins.py`

Hereda de ViewSet:

```python
class TenantViewSetMixin:
    def get_queryset(self):
        self._set_tenant_context()  # Setea ContextVar desde request
        
        user = self.request.user
        if user.is_superuser:
            return self.model.all_objects.all()
        
        empresa = self.get_empresa()
        return self.model.objects.filter(empresa=empresa)
    
    def perform_create(self, serializer):
        self._set_tenant_context()
        serializer.save()  # BaseModel.save() lee contexto
    
    def _set_tenant_context(self):
        set_current_empresa(self.get_empresa())
        set_current_user(self.request.user)
    
    def get_empresa(self):
        # Retorna empresa_activa del usuario
        return self.request.user.empresa_activa
```

## Flujo completo: Ejemplo request

```
1. Cliente envia GET /api/presupuestos/ con Cookie acceso_token=eyJ...

2. Middleware EmpresaMiddleware:
   - Lee request.user.is_authenticated
   - Obtiene empresa_activa del usuario
   - set_current_empresa(empresa)

3. DRF authentication:
   - CookieJWTAuthentication busca JWT en cookie
   - Valida JWT, obtiene User
   - request.user = User instance

4. Permisos:
   a) IsAuthenticated -> request.user.is_authenticated? SI -> Continua
   b) TieneRelacionActiva -> UserEmpresa.activo=True? SI -> Continua
   c) TienePermisoModuloAccion:
      - action="list" -> accion=VER
      - user.tiene_permiso(PRESUPUESTOS, VER, empresa_activa)? SI -> Continua

5. ViewSet.list():
   - get_queryset() filtra por empresa actual (manager automatico)
   - Retorna presupuestos de empresa activa SOLO

6. Respuesta:
   - Status 200 OK
   - Body: [{ presupuesto1 }, { presupuesto2 }, ...] (solo empresa actual)

Resultado: Usuario ve SOLO presupuestos de su empresa actual, no de otras.
```

## Notas de seguridad

1. **HttpOnly cookies**: Impermeables a XSS (JS no puede acceder).
2. **CSRF tokens**: Validado en unsafe methods para prevenir ataques cross-site.
3. **JWT expiration**: Access tokens corta vida (15 min), refresh tokens larga vida (7 dias).
4. **Tenancy**: Managers filtran automaticamente por empresa activa; imposible acceder cross-tenant.
5. **Permisos granulares**: Por modulo + accion; facil audit y customizacion.
6. **Superuser bypass**: Solo para admin/staff; no para usuarios normales.
