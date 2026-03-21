import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ComprasRecepcionesListPage from '@/modules/compras/pages/ComprasRecepcionesListPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

function authState(permissions = ['COMPRAS.VER']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'recepciones@eldanor.cl',
        permissions,
      },
      empresas: [],
      empresasStatus: 'idle',
      empresasError: null,
      changingEmpresaId: null,
      isAuthenticated: true,
      status: 'idle',
      bootstrapStatus: 'idle',
      error: null,
    },
  }
}

describe('compras/RecepcionesListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('oculta acciones operativas en borrador sin permisos de crear editar aprobar', async () => {
    server.use(
      http.get('*/recepciones-compra/', async () =>
        HttpResponse.json([
          { id: 'rec-1', orden_compra: 'oc-1', fecha: '2026-03-12', estado: 'BORRADOR', observaciones: '' },
        ]),
      ),
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-1', numero: 'OC-001', proveedor: 'p-1' },
        ]),
      ),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'b-1', nombre: 'Principal' }])),
    )

    renderWithProviders(<ComprasRecepcionesListPage />, {
      preloadedState: authState(['COMPRAS.VER']),
    })

    expect(await screen.findByText('OC-001')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nueva recepcion' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
  })

  it('muestra solo ver cuando la recepcion ya esta confirmada', async () => {
    server.use(
      http.get('*/recepciones-compra/', async () =>
        HttpResponse.json([
          { id: 'rec-2', orden_compra: 'oc-2', fecha: '2026-03-13', estado: 'CONFIRMADA', observaciones: '' },
        ]),
      ),
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-2', numero: 'OC-002', proveedor: 'p-1' },
        ]),
      ),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'b-1', nombre: 'Principal' }])),
    )

    renderWithProviders(<ComprasRecepcionesListPage />, {
      preloadedState: authState(['COMPRAS.VER', 'COMPRAS.EDITAR', 'COMPRAS.APROBAR']),
    })

    expect(await screen.findByText('OC-002')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
  })
})
