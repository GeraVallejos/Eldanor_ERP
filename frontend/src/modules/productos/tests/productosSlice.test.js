import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import {
  createProducto,
  fetchCatalogosProducto,
  fetchProductos,
  selectProductos,
} from '@/modules/productos/productosSlice'
import { logout } from '@/modules/auth/authSlice'
import { server } from '@/test/msw/server'
import { createTestStore } from '@/test/utils/createTestStore'

describe('productosSlice', () => {
  it('carga productos desde backend y normaliza lista', async () => {
    const store = createTestStore()

    const result = await store.dispatch(fetchProductos())

    expect(result.type).toBe('productos/fetchProductos/fulfilled')
    expect(selectProductos(store.getState())).toHaveLength(1)
    expect(selectProductos(store.getState())[0].nombre).toBe('Servicio de poda')
  })

  it('crea producto y persiste en estado local', async () => {
    const requestPayload = {
      nombre: 'Motosierra',
      descripcion: 'Herramienta de corte',
      sku: 'PROD-100',
      tipo: 'PRODUCTO',
      categoria: 1,
      impuesto: 1,
      precio_referencia: 99000,
      precio_costo: 55000,
      maneja_inventario: true,
      stock_actual: 3,
      activo: true,
    }

    const store = createTestStore()

    const result = await store.dispatch(createProducto(requestPayload))

    expect(result.type).toBe('productos/createProducto/fulfilled')
    expect(selectProductos(store.getState())[0]).toMatchObject({
      id: 101,
      nombre: 'Motosierra',
      sku: 'PROD-100',
    })
  })

  it('fetch de catalogos integra dos endpoints y actualiza ambos datasets', async () => {
    const store = createTestStore()

    const result = await store.dispatch(fetchCatalogosProducto())

    expect(result.type).toBe('productos/fetchCatalogosProducto/fulfilled')
    expect(store.getState().productos.categorias).toHaveLength(1)
    expect(store.getState().productos.impuestos).toHaveLength(1)
  })

  it('logout de auth limpia estado de productos (integracion entre modulos)', () => {
    const store = createTestStore({
      auth: {
        user: { id: 1, email: 'admin@eldanor.cl' },
        empresas: [],
        empresasStatus: 'idle',
        empresasError: null,
        changingEmpresaId: null,
        isAuthenticated: true,
        status: 'succeeded',
        bootstrapStatus: 'succeeded',
        error: null,
      },
      productos: {
        items: [{ id: 300, nombre: 'Temporal' }],
        status: 'succeeded',
        error: null,
        createStatus: 'idle',
        createError: null,
        categorias: [{ id: 1, nombre: 'General' }],
        impuestos: [{ id: 1, nombre: 'IVA' }],
        catalogStatus: 'succeeded',
        catalogError: null,
      },
    })

    store.dispatch(logout())

    expect(store.getState().productos.items).toEqual([])
    expect(store.getState().productos.status).toBe('idle')
    expect(store.getState().productos.catalogStatus).toBe('idle')
  })

  it('valida contrato request/response al crear producto (frontend-backend)', async () => {
    let capturedBody = null

    server.use(
      http.post('*/productos/', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json({ id: 999, ...capturedBody }, { status: 201 })
      }),
    )

    const store = createTestStore()
    const payload = {
      nombre: 'Fertilizante',
      descripcion: '',
      sku: 'PROD-200',
      tipo: 'PRODUCTO',
      categoria: null,
      impuesto: null,
      precio_referencia: 12000,
      precio_costo: 8000,
      maneja_inventario: true,
      stock_actual: 20,
      activo: true,
    }

    const result = await store.dispatch(createProducto(payload))

    expect(result.type).toBe('productos/createProducto/fulfilled')
    expect(capturedBody).toMatchObject({
      nombre: 'Fertilizante',
      sku: 'PROD-200',
      precio_referencia: 12000,
    })
    expect(selectProductos(store.getState())[0].id).toBe(999)
  })
})
