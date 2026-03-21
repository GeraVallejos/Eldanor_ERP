import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ComprasDocumentosListPage from '@/modules/compras/pages/ComprasDocumentosListPage'
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
        email: 'documentos@eldanor.cl',
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

describe('compras/DocumentosListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('oculta acciones operativas sin permisos aunque el estado las permita', async () => {
    server.use(
      http.get('*/documentos-compra/', async () =>
        HttpResponse.json([
          {
            id: 'doc-1',
            proveedor: 'p-1',
            tipo_documento: 'FACTURA_COMPRA',
            folio: 'F-101',
            fecha_emision: '2026-03-10',
            estado: 'BORRADOR',
            estado_contable: 'PENDIENTE',
            total: 10000,
          },
        ]),
      ),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
    )

    renderWithProviders(<ComprasDocumentosListPage />, {
      preloadedState: authState(['COMPRAS.VER']),
    })

    expect(await screen.findByText('F-101')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nuevo documento' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Duplicar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Anular' })).not.toBeInTheDocument()
  })

  it('muestra acciones validas para documento confirmado cuando el usuario si puede operar', async () => {
    server.use(
      http.get('*/documentos-compra/', async () =>
        HttpResponse.json([
          {
            id: 'doc-2',
            proveedor: 'p-1',
            tipo_documento: 'GUIA_RECEPCION',
            folio: 'G-202',
            fecha_emision: '2026-03-10',
            estado: 'CONFIRMADO',
            estado_contable: 'PENDIENTE',
            total: 15000,
          },
        ]),
      ),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
    )

    renderWithProviders(<ComprasDocumentosListPage />, {
      preloadedState: authState(['COMPRAS.VER', 'COMPRAS.CREAR', 'COMPRAS.EDITAR', 'COMPRAS.ANULAR']),
    })

    expect(await screen.findByText('G-202')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Corregir' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Duplicar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anular' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
  })
})
