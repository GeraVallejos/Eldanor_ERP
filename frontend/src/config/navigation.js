import {
  Boxes,
  ClipboardList,
  Handshake,
  PackagePlus,
  ShoppingBag,
  ShieldCheck,
  CircleDollarSign,
} from 'lucide-react'
import { hasPermission } from '@/modules/shared/auth/permissions'

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
      {
        id: 'productos-categorias',
        label: 'Categorias',
        to: '/productos/categorias',
        enabled: true,
      },
      {
        id: 'productos-impuestos',
        label: 'Impuestos',
        to: '/productos/impuestos',
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
    id: 'auditoria',
    label: 'Auditoria',
    icon: ShieldCheck,
    enabled: true,
    requiredPermissions: ['AUDITORIA.VER'],
    children: [
      {
        id: 'auditoria-eventos',
        label: 'Eventos',
        to: '/auditoria/eventos',
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
        label: 'Documentos tributarios (Guias/Facturas)',
        to: '/compras/documentos',
        enabled: true,
      },
    ],
  },
  {
    id: 'ventas',
    label: 'Ventas',
    icon: CircleDollarSign,
    enabled: true,
    requiredPermissions: ['VENTAS.VER'],
    children: [
      {
        id: 'ventas-pedidos',
        label: 'Pedidos',
        to: '/ventas/pedidos',
        enabled: true,
      },
      {
        id: 'ventas-guias',
        label: 'Guias de despacho',
        to: '/ventas/guias',
        enabled: true,
      },
      {
        id: 'ventas-facturas',
        label: 'Facturas',
        to: '/ventas/facturas',
        enabled: true,
      },
      {
        id: 'ventas-notas',
        label: 'Notas de credito',
        to: '/ventas/notas',
        enabled: true,
      },
    ],
  },
]

function hasRequiredPermissions(userPermissions, requiredPermissions) {
  if (!requiredPermissions?.length) {
    return true
  }

  const mockUser = { permissions: userPermissions }
  return requiredPermissions.every((permission) => hasPermission(mockUser, permission))
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
