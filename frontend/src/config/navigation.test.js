import { describe, expect, it } from 'vitest'
import { resolveNavigation } from '@/config/navigation'

describe('resolveNavigation', () => {
  it('oculta productos, contactos y presupuestos cuando faltan permisos de visualizacion', () => {
    const modules = resolveNavigation({
      permissions: ['COMPRAS.VER', 'TESORERIA.VER', 'FACTURACION.VER'],
    })

    const ids = modules.map((module) => module.id)
    expect(ids).not.toContain('productos')
    expect(ids).not.toContain('contactos')
    expect(ids).not.toContain('presupuestos')
    expect(ids).toContain('compras')
    expect(ids).toContain('tesoreria')
    expect(ids).toContain('facturacion')
  })

  it('muestra ventas cuando el usuario solo puede ver presupuestos', () => {
    const modules = resolveNavigation({
      permissions: ['PRESUPUESTOS.VER'],
    })

    const ventas = modules.find((module) => module.id === 'ventas')
    expect(ventas).toBeDefined()
    expect(ventas.children.map((item) => item.id)).toContain('ventas-presupuestos')
  })

  it('mantiene el modulo cuando el usuario tiene permiso wildcard del modulo', () => {
    const modules = resolveNavigation({
      permissions: ['PRODUCTOS.*'],
    })

    expect(modules.map((module) => module.id)).toContain('productos')
  })

  it('muestra administracion de productos cuando el usuario tiene algun permiso de gestion valido', () => {
    const modules = resolveNavigation({
      permissions: ['PRODUCTOS.VER', 'PRODUCTOS.CREAR'],
    })

    const productos = modules.find((module) => module.id === 'productos')
    expect(productos).toBeDefined()
    expect(productos.children.map((item) => item.id)).toContain('productos-categorias')
    expect(productos.children.map((item) => item.id)).toContain('productos-impuestos')
    expect(productos.children.map((item) => item.id)).toContain('productos-listas-precio')
  })
})
