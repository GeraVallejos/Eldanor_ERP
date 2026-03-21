import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioTrasladosPage from '@/modules/inventario/pages/InventarioTrasladosPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioTrasladosPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('registra un traslado entre bodegas y muestra stock origen', async () => {
    let trasladoPayload = null

    server.use(
      http.get('*/stocks/', async () => HttpResponse.json([{ id: 'st-1', producto: 'prod-2', bodega: 'bod-1', stock: '5.00' }])),
      http.get('*/movimientos-inventario/', async () =>
        HttpResponse.json([
          {
            id: 'tras-10',
            documento_tipo: 'TRASLADO',
            producto_id: 'prod-2',
            bodega_origen_id: 'bod-1',
            bodega_destino_id: 'bod-2',
            referencia: 'Reposicion sucursal',
            tipo: 'TRASLADO',
            cantidad: '1.00',
            creado_en: '2026-03-20T11:00:00Z',
          },
        ]),
      ),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-2', nombre: 'Motosierra' }])),
      http.get('*/bodegas/', async () =>
        HttpResponse.json([
          { id: 'bod-1', nombre: 'Principal' },
          { id: 'bod-2', nombre: 'Secundaria' },
        ]),
      ),
      http.post('*/movimientos-inventario/trasladar/', async ({ request }) => {
        trasladoPayload = await request.json()
        return HttpResponse.json({ traslado_id: 'tras-1' }, { status: 201 })
      }),
    )

    renderWithProviders(<InventarioTrasladosPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 'user-1',
            email: 'inventario@eldanor.cl',
            permissions: ['INVENTARIO.VER', 'INVENTARIO.EDITAR'],
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
      },
    })

    expect(await screen.findByRole('heading', { name: 'Traslados entre bodegas' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Historial de traslados' })).toBeInTheDocument()
    expect(await screen.findByText('Reposicion sucursal')).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Producto traslado'))
    await userEvent.type(screen.getByLabelText('Producto traslado'), 'Moto{enter}')
    await userEvent.click(screen.getByLabelText('Bodega origen'))
    await userEvent.type(screen.getByLabelText('Bodega origen'), 'Prin{enter}')
    await userEvent.click(screen.getByLabelText('Bodega destino'))
    await userEvent.type(screen.getByLabelText('Bodega destino'), 'Secu{enter}')
    await userEvent.type(screen.getByLabelText('Cantidad'), '2')
    await userEvent.click(screen.getByRole('button', { name: 'Registrar traslado' }))

    await waitFor(() => {
      expect(trasladoPayload).toMatchObject({
        producto_id: 'prod-2',
        bodega_origen_id: 'bod-1',
        bodega_destino_id: 'bod-2',
        cantidad: '2',
        referencia: 'Traslado interno prod-2',
      })
    })

    await userEvent.type(screen.getByLabelText('Buscar referencia'), 'sucursal')
    expect(screen.getByDisplayValue('sucursal')).toBeInTheDocument()
  })
})
