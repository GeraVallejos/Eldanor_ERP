import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import ProductosListPage from '@/modules/productos/pages/ProductosListPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('productos/ProductosListPage', () => {
  const productosMixtos = [
    {
      id: 100,
      nombre: 'Martillo profesional',
      sku: 'PROD-001',
      tipo: 'PRODUCTO',
      precio_referencia: 22000,
      precio_costo: 14000,
      stock_actual: 6,
      maneja_inventario: true,
      activo: true,
    },
    {
      id: 101,
      nombre: 'Servicio de poda',
      sku: 'SERV-001',
      tipo: 'SERVICIO',
      precio_referencia: 15000,
      precio_costo: 7000,
      stock_actual: 0,
      maneja_inventario: false,
      activo: true,
    },
  ]

  function buildProductosResponse(request) {
    const url = new URL(request.url)
    const tipo = url.searchParams.get('tipo')
    const page = Number(url.searchParams.get('page') || 1)
    const pageSize = Number(url.searchParams.get('page_size') || productosMixtos.length)

    let results = productosMixtos
    if (tipo) {
      results = productosMixtos.filter((item) => item.tipo === tipo)
    }

    return HttpResponse.json({
      count: results.length,
      results: results.slice((page - 1) * pageSize, page * pageSize),
    })
  }

  it('oculta acciones de escritura cuando el usuario solo tiene permiso de lectura', async () => {
    server.use(
      http.get('*/productos/', async ({ request }) => buildProductosResponse(request)),
    )

    renderWithProviders(<ProductosListPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 10,
            email: 'lector@erp.test',
            permissions: ['PRODUCTOS.VER'],
          },
          empresas: [],
          empresasStatus: 'idle',
          empresasError: null,
          changingEmpresaId: null,
          isAuthenticated: true,
          status: 'succeeded',
          bootstrapStatus: 'succeeded',
          error: null,
        },
      },
    })

    expect(await screen.findByText('Martillo profesional')).toBeInTheDocument()
    expect(screen.queryByText('Servicio de poda')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nuevo producto' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument()
  })

  it('no muestra carga masiva si el usuario no cumple la regla de rol admin', async () => {
    server.use(
      http.get('*/productos/', async ({ request }) => buildProductosResponse(request)),
    )

    renderWithProviders(<ProductosListPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 11,
            email: 'owner@erp.test',
            rol: 'OWNER',
            permissions: ['PRODUCTOS.VER', 'PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'],
          },
          empresas: [],
          empresasStatus: 'idle',
          empresasError: null,
          changingEmpresaId: null,
          isAuthenticated: true,
          status: 'succeeded',
          bootstrapStatus: 'succeeded',
          error: null,
        },
      },
    })

    expect(await screen.findByText('Martillo profesional')).toBeInTheDocument()
    expect(screen.queryByText(/Carga masiva/i)).not.toBeInTheDocument()
  })

  it('permite cambiar a servicios desde el filtro por tipo', async () => {
    const user = userEvent.setup()
    server.use(
      http.get('*/productos/', async ({ request }) => buildProductosResponse(request)),
    )

    renderWithProviders(<ProductosListPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 12,
            email: 'viewer@erp.test',
            permissions: ['PRODUCTOS.VER'],
          },
          empresas: [],
          empresasStatus: 'idle',
          empresasError: null,
          changingEmpresaId: null,
          isAuthenticated: true,
          status: 'succeeded',
          bootstrapStatus: 'succeeded',
          error: null,
        },
      },
    })

    expect(await screen.findByText('Martillo profesional')).toBeInTheDocument()
    expect(screen.queryByText('Servicio de poda')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Servicios' }))

    expect(await screen.findByText('Servicio de poda')).toBeInTheDocument()
    expect(screen.queryByText('Martillo profesional')).not.toBeInTheDocument()
  })
})
