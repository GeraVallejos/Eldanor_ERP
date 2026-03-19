# Guía de Permisos en Frontend

## Resumen

El sistema de permisos del frontend sigue el mismo modelo que el backend: cada acción requiere un código de permiso del formato `MODULO.ACCION`. Los hooks centralizados en `shared/auth/usePermission.js` son la única forma recomendada de verificar permisos en componentes React.

---

## Arquitectura

```
src/modules/shared/auth/
  permissions.js       ← lógica pura (sin React), fuente de verdad
  usePermission.js     ← hooks React que consumen la lógica pura
```

### `permissions.js`

Exporta `hasPermission(user, code)` con soporte para:

| Código              | Significado                              |
|---------------------|------------------------------------------|
| `*`                 | Superusuario — accede a todo             |
| `MODULO.*`          | Acceso completo al módulo                |
| `MODULO.ACCION`     | Acción específica dentro del módulo      |

También exporta helpers de dominio como `canManagePresupuestoStatus(user, from, to)`.

### `usePermission.js`

```js
import { usePermission, usePermissions } from '@/modules/shared/auth/usePermission'
```

#### `usePermission(code)`

Retorna un booleano. Útil cuando se necesita verificar un solo permiso.

```jsx
const canCreate = usePermission('VENTAS.CREAR')

return <button disabled={!canCreate}>Nuevo Pedido</button>
```

#### `usePermissions([codes])`

Retorna un objeto `{ [code]: boolean }`. Útil cuando se necesitan múltiples permisos en el mismo componente.

```jsx
const { 'VENTAS.CREAR': canCreate, 'VENTAS.EDITAR': canEdit } = usePermissions([
  'VENTAS.CREAR',
  'VENTAS.EDITAR',
])
```

---

## Convenciones

### ✅ Correcto — usar los hooks en componentes

```jsx
import { usePermission, usePermissions } from '@/modules/shared/auth/usePermission'
import { MI_MODULO_PERMISSIONS } from '../constants'

function MiListPage() {
  const { [MI_MODULO_PERMISSIONS.crear]: canCreate } = usePermissions([
    MI_MODULO_PERMISSIONS.crear,
    MI_MODULO_PERMISSIONS.editar,
  ])

  return (
    <>
      {canCreate && <Link to="nuevo">Crear</Link>}
    </>
  )
}
```

### ❌ Incorrecto — importar `hasPermission` directamente en componentes

```jsx
// NUNCA hacer esto en un componente React
import { hasPermission } from '@/modules/shared/auth/permissions'
import { useSelector } from 'react-redux'
import { selectCurrentUser } from '@/store/authSlice'

function MiPage() {
  const user = useSelector(selectCurrentUser)
  const canCreate = hasPermission(user, 'MODULO.CREAR') // ← patrón obsoleto
}
```

> `hasPermission` está disponible para uso en contextos no-React (ej: `navigation.js`, utilidades puras, tests).

---

## Constantes de Permisos por Módulo

Cada módulo debe definir sus constantes en `constants.js`:

```js
// src/modules/mi_modulo/constants.js
export const MI_MODULO_PERMISSIONS = {
  ver:    'MI_MODULO.VER',
  crear:  'MI_MODULO.CREAR',
  editar: 'MI_MODULO.EDITAR',
  borrar: 'MI_MODULO.BORRAR',
}
```

Usar las constantes en lugar de strings crudos para evitar errores tipográficos:

```jsx
// ✅ con constante
const canEdit = usePermission(MI_MODULO_PERMISSIONS.editar)

// ❌ con string crudo (frágil)
const canEdit = usePermission('MI_MODULO.EDITAR')
```

---

## Patrón para FormPages (crear vs. editar)

```jsx
function MiFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)

  const canCreate = usePermission(MI_MODULO_PERMISSIONS.crear)
  const canEdit   = usePermission(MI_MODULO_PERMISSIONS.editar)
  const canSubmit = isEdit ? canEdit : canCreate

  return (
    <form onSubmit={handleSubmit}>
      {!canSubmit && (
        <p className="text-red-500">No tienes permiso para esta acción.</p>
      )}
      <button type="submit" disabled={saving || !canSubmit}>
        Guardar
      </button>
    </form>
  )
}
```

---

## Patrón para ListPages

```jsx
function MiListPage() {
  const {
    [MI_MODULO_PERMISSIONS.crear]:  canCreate,
    [MI_MODULO_PERMISSIONS.editar]: canEdit,
    [MI_MODULO_PERMISSIONS.borrar]: canDelete,
  } = usePermissions([
    MI_MODULO_PERMISSIONS.crear,
    MI_MODULO_PERMISSIONS.editar,
    MI_MODULO_PERMISSIONS.borrar,
  ])

  return (
    <>
      {canCreate && <Link to="nuevo">Nuevo</Link>}
      <table>
        {items.map(item => (
          <tr key={item.id}>
            <td>{item.nombre}</td>
            {canEdit && <td><Link to={`${item.id}/editar`}>Editar</Link></td>}
            {canDelete && <td><button onClick={() => handleDelete(item.id)}>Eliminar</button></td>}
          </tr>
        ))}
      </table>
    </>
  )
}
```

---

## Tests

En tests, inyectar el usuario con permisos usando `createTestStore`:

```js
// usuario con permiso específico
const store = createTestStore({
  auth: { user: { permissions: ['MI_MODULO.CREAR'] } }
})

// usuario sin permisos
const storeReadOnly = createTestStore({
  auth: { user: { permissions: ['MI_MODULO.VER'] } }
})

// superusuario
const storeAdmin = createTestStore({
  auth: { user: { permissions: ['*'] } }
})
```

Usar `renderWithProviders(component, { store })` para montar el componente con el store correcto.

---

## Módulos que ya usan este patrón

| Módulo        | Archivos                                                          |
|---------------|-------------------------------------------------------------------|
| ventas        | `VentasPedidosListPage`, `VentasGuiasListPage`, `VentasFacturasListPage`, `VentasNotasListPage`, `VentasPedidosDetailPage`, todas las `*FormPage` |
| presupuestos  | `PresupuestosListPage`                                            |

Al agregar un módulo nuevo, seguir el mismo patrón desde el inicio.
