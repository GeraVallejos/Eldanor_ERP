import {
  Boxes,
  ClipboardList,
  Handshake,
  PackagePlus,
  ShoppingBag,
} from 'lucide-react'

const NAV_MODULES = [
  {
    id: 'productos',
    label: 'Productos',
    icon: ShoppingBag,
    enabled: true,
    children: [
      {
        id: 'productos-listado',
        label: 'Listado',
        to: '/productos',
        enabled: true,
      },
    ],
  },
  {
    id: 'contactos',
    label: 'Contactos',
    icon: Handshake,
    enabled: true,
    children: [
      {
        id: 'contactos-clientes-listado',
        label: 'Clientes',
        to: '/contactos/clientes',
        enabled: true,
      },
      {
        id: 'contactos-proveedores-listado',
        label: 'Proveedores',
        to: '/contactos/proveedores',
        enabled: true,
      },
    ],
  },
  {
    id: 'presupuestos',
    label: 'Presupuestos',
    icon: ClipboardList,
    enabled: true,
    children: [
      {
        id: 'presupuestos-listado',
        label: 'Listado',
        to: '/presupuestos',
        enabled: true,
      },
    ],
  },
  {
    id: 'inventario',
    label: 'Inventario',
    icon: Boxes,
    enabled: true,
    requiredPermissions: ['PRODUCTOS.VER'],
    children: [
      {
        id: 'inventario-kardex',
        label: 'Kardex',
        to: '/inventario/kardex',
        enabled: true,
      },
      {
        id: 'inventario-resumen',
        label: 'Resumen valorizado',
        to: '/inventario/resumen',
        enabled: true,
      },
    ],
  },
  {
    id: 'compras',
    label: 'Compras',
    icon: PackagePlus,
    enabled: true,
    requiredPermissions: ['COMPRAS.VER'],
    children: [
      {
        id: 'compras-ordenes',
        label: 'Ordenes',
        to: '/compras/ordenes',
        enabled: true,
      },
      {
        id: 'compras-documentos',
        label: 'Documentos (Guias/Facturas)',
        to: '/compras/documentos',
        enabled: true,
      },
    ],
  },
]

function hasRequiredPermissions(userPermissions, requiredPermissions) {
  if (!requiredPermissions?.length) {
    return true
  }

  const normalizedUserPermissions = userPermissions.map((permission) => String(permission || '').trim().toUpperCase())

  return requiredPermissions.every((permission) => {
    const target = String(permission || '').trim().toUpperCase()
    if (!target) {
      return true
    }

    if (normalizedUserPermissions.includes('*') || normalizedUserPermissions.includes(target)) {
      return true
    }

    const [moduleCode] = target.split('.')
    return Boolean(moduleCode) && normalizedUserPermissions.includes(`${moduleCode}.*`)
  })
}

function hasRequiredRoles(userRoles, requiredRoles) {
  if (!requiredRoles?.length) {
    return true
  }

  return requiredRoles.some((role) => userRoles.includes(role))
}

export function resolveNavigation(user) {
  const userPermissions = Array.isArray(user?.permissions) ? user.permissions : []
  const userRoles = Array.isArray(user?.roles) ? user.roles : []

  return NAV_MODULES
    .filter((module) => module.enabled !== false)
    .filter((module) => hasRequiredPermissions(userPermissions, module.requiredPermissions))
    .filter((module) => hasRequiredRoles(userRoles, module.requiredRoles))
    .map((module) => {
      const children = (module.children || [])
        .filter((item) => item.enabled !== false)
        .filter((item) => hasRequiredPermissions(userPermissions, item.requiredPermissions))
        .filter((item) => hasRequiredRoles(userRoles, item.requiredRoles))

      return {
        ...module,
        children,
      }
    })
    .filter((module) => module.to || module.children.length > 0)
}
