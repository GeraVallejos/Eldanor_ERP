import {
  Banknote,
  Boxes,
  ClipboardList,
  Handshake,
  KeyRound,
  PackagePlus,
  ShoppingBag,
  ShieldCheck,
  CircleDollarSign,
  Landmark,
} from 'lucide-react'
import { hasAnyPermission, hasPermission } from '@/modules/shared/auth/permissions'
import { PRODUCTOS_MANAGE_ANY } from '@/config/productosAccess'

const NAV_MODULES = [
  {
    id: 'productos',
    label: 'Productos',
    icon: ShoppingBag,
    enabled: true,
    requiredPermissions: ['PRODUCTOS.VER'],
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
        requiredAnyPermissions: PRODUCTOS_MANAGE_ANY,
      },
      {
        id: 'productos-impuestos',
        label: 'Impuestos',
        to: '/productos/impuestos',
        enabled: true,
        requiredAnyPermissions: PRODUCTOS_MANAGE_ANY,
      },
      {
        id: 'productos-listas-precio',
        label: 'Listas de precio',
        to: '/productos/listas-precio',
        enabled: true,
        requiredAnyPermissions: PRODUCTOS_MANAGE_ANY,
      },
    ],
  },
  {
    id: 'contactos',
    label: 'Contactos',
    icon: Handshake,
    enabled: true,
    requiredPermissions: ['CONTACTOS.VER'],
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
    id: 'inventario',
    label: 'Inventario',
    icon: Boxes,
    enabled: true,
    requiredPermissions: ['INVENTARIO.VER'],
    children: [
      {
        id: 'inventario-bodegas',
        label: 'Bodegas',
        to: '/inventario/bodegas',
        enabled: true,
      },
      {
        id: 'inventario-ajustes',
        label: 'Ajustes',
        to: '/inventario/ajustes',
        enabled: true,
        requiredPermissions: ['INVENTARIO.EDITAR'],
      },
      {
        id: 'inventario-kardex',
        label: 'Kardex',
        to: '/inventario/kardex',
        enabled: true,
      },
      {
        id: 'inventario-resumen',
        label: 'Resumen',
        to: '/inventario/resumen',
        enabled: true,
      },
      {
        id: 'inventario-reportes',
        label: 'Reportes',
        to: '/inventario/reportes',
        enabled: true,
      },
      {
        id: 'inventario-traslados',
        label: 'Traslados',
        to: '/inventario/traslados',
        enabled: true,
        requiredPermissions: ['INVENTARIO.EDITAR'],
      },
    ],
  },
  {
    id: 'tesoreria',
    label: 'Tesoreria',
    icon: Banknote,
    enabled: true,
    requiredPermissions: ['TESORERIA.VER'],
    children: [
      {
        id: 'tesoreria-bancos',
        label: 'Bancos y conciliacion',
        to: '/tesoreria/bancos',
        enabled: true,
      },
      {
        id: 'tesoreria-cartera',
        label: 'Cartera',
        to: '/tesoreria/cartera',
        enabled: true,
      },
      {
        id: 'tesoreria-monedas',
        label: 'Monedas',
        to: '/tesoreria/monedas',
        enabled: true,
      },
      {
        id: 'tesoreria-tipos-cambio',
        label: 'Tipos de cambio',
        to: '/tesoreria/tipos-cambio',
        enabled: true,
      },
    ],
  },
  {
    id: 'contabilidad',
    label: 'Contabilidad',
    icon: Landmark,
    enabled: true,
    children: [
      {
        id: 'contabilidad-plan-cuentas',
        label: 'Plan de cuentas',
        to: '/contabilidad/plan-cuentas',
        enabled: true,
        requiredPermissions: ['CONTABILIDAD.VER'],
      },
      {
        id: 'contabilidad-asientos',
        label: 'Asientos',
        to: '/contabilidad/asientos',
        enabled: true,
        requiredPermissions: ['CONTABILIDAD.VER'],
      },
      {
        id: 'contabilidad-reportes',
        label: 'Reportes',
        to: '/contabilidad/reportes',
        enabled: true,
        requiredPermissions: ['CONTABILIDAD.VER'],
      },
    ],
  },
  {
    id: 'facturacion',
    label: 'Facturacion',
    icon: Landmark,
    enabled: true,
    requiredPermissions: ['FACTURACION.VER'],
    children: [
      {
        id: 'facturacion-sii',
        label: 'SII y DTE',
        to: '/facturacion/sii',
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
    id: 'administracion',
    label: 'Administracion',
    icon: KeyRound,
    enabled: true,
    requiredPermissions: ['ADMINISTRACION.GESTIONAR_PERMISOS'],
    children: [
      {
        id: 'administracion-permisos',
        label: 'Permisos',
        to: '/administracion/permisos',
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
        id: 'compras-resumen',
        label: 'Resumen',
        to: '/compras/resumen',
        enabled: true,
      },
      {
        id: 'compras-ordenes',
        label: 'Ordenes',
        to: '/compras/ordenes',
        enabled: true,
      },
      {
        id: 'compras-reportes',
        label: 'Reportes',
        to: '/compras/reportes',
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
    children: [
      {
        id: 'ventas-resumen',
        label: 'Resumen',
        to: '/ventas/resumen',
        enabled: true,
        requiredPermissions: ['VENTAS.VER'],
      },
      {
        id: 'ventas-presupuestos',
        label: 'Presupuestos',
        to: '/presupuestos',
        enabled: true,
        requiredPermissions: ['PRESUPUESTOS.VER'],
      },
      {
        id: 'ventas-pedidos',
        label: 'Pedidos',
        to: '/ventas/pedidos',
        enabled: true,
        requiredPermissions: ['VENTAS.VER'],
      },
      {
        id: 'ventas-guias',
        label: 'Guias de despacho',
        to: '/ventas/guias',
        enabled: true,
        requiredPermissions: ['VENTAS.VER'],
      },
      {
        id: 'ventas-facturas',
        label: 'Facturas',
        to: '/ventas/facturas',
        enabled: true,
        requiredPermissions: ['VENTAS.VER'],
      },
      {
        id: 'ventas-notas',
        label: 'Notas de credito',
        to: '/ventas/notas',
        enabled: true,
        requiredPermissions: ['VENTAS.VER'],
      },
      {
        id: 'ventas-reportes',
        label: 'Reportes',
        to: '/ventas/reportes',
        enabled: true,
        requiredPermissions: ['VENTAS.VER'],
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

function hasRequiredAnyPermissions(userPermissions, requiredPermissions) {
  if (!requiredPermissions?.length) {
    return true
  }

  const mockUser = { permissions: userPermissions }
  return hasAnyPermission(mockUser, requiredPermissions)
}

function hasRequiredRoles(userRoles, requiredRoles) {
  if (!requiredRoles?.length) {
    return true
  }

  return requiredRoles.some((role) => userRoles.includes(role))
}

export function resolveNavigation(user) {
  const userPermissions = Array.isArray(user?.permissions) ? user.permissions : []
  const userRoles = Array.isArray(user?.roles)
    ? user.roles
    : user?.rol
      ? [user.rol]
      : []

  return NAV_MODULES
    .filter((module) => module.enabled !== false)
    .filter((module) => hasRequiredPermissions(userPermissions, module.requiredPermissions))
    .filter((module) => hasRequiredAnyPermissions(userPermissions, module.requiredAnyPermissions))
    .filter((module) => hasRequiredRoles(userRoles, module.requiredRoles))
    .map((module) => {
      const children = (module.children || [])
        .filter((item) => item.enabled !== false)
        .filter((item) => hasRequiredPermissions(userPermissions, item.requiredPermissions))
        .filter((item) => hasRequiredAnyPermissions(userPermissions, item.requiredAnyPermissions))
        .filter((item) => hasRequiredRoles(userRoles, item.requiredRoles))

      return {
        ...module,
        children,
      }
    })
    .filter((module) => module.to || module.children.length > 0)
}
