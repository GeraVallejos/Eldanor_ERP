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
    await userEvent.click(screen.getByLabelText('Producto traslado'))
    await userEvent.type(screen.getByLabelText('Producto traslado'), 'Moto{enter}')
    await userEvent.click(screen.getByLabelText('Bodega origen'))
    await userEvent.type(screen.getByLabelText('Bodega origen'), 'Prin{enter}')
    await userEvent.click(screen.getByLabelText('Bodega destino'))
    await userEvent.type(screen.getByLabelText('Bodega destino'), 'Secu{enter}')
    await userEvent.type(screen.getByLabelText('Cantidad'), '2')
    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Reposicion sucursal')
    await userEvent.type(screen.getByLabelText('Referencia operativa'), 'SOL-88')
    await userEvent.type(screen.getByLabelText('Observaciones'), 'Mover a zona de despacho')
    await userEvent.click(screen.getByRole('button', { name: 'Registrar traslado' }))

    await waitFor(() => {
      expect(trasladoPayload).toMatchObject({
        producto_id: 'prod-2',
        bodega_origen_id: 'bod-1',
        bodega_destino_id: 'bod-2',
        cantidad: '2',
        referencia: 'Reposicion sucursal | SOL-88 | Mover a zona de despacho',
      })
    })

  })

  it('muestra error del contrato API al registrar un traslado', async () => {
    server.use(
      http.get('*/stocks/', async () => HttpResponse.json([{ id: 'st-1', producto: 'prod-2', bodega: 'bod-1', stock: '1.00' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-2', nombre: 'Motosierra' }])),
      http.get('*/bodegas/', async () =>
        HttpResponse.json([
          { id: 'bod-1', nombre: 'Principal' },
          { id: 'bod-2', nombre: 'Secundaria' },
        ]),
      ),
      http.post('*/movimientos-inventario/trasladar/', async () =>
        HttpResponse.json(
          {
            detail: 'Stock insuficiente para Motosierra: disponible 1.00.',
            error_code: 'BUSINESS_RULE_ERROR',
          },
          { status: 400 },
        ),
      ),
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

    await screen.findByRole('heading', { name: 'Traslados entre bodegas' })
    await userEvent.click(screen.getByLabelText('Producto traslado'))
    await userEvent.type(screen.getByLabelText('Producto traslado'), 'Moto{enter}')
    await userEvent.click(screen.getByLabelText('Bodega origen'))
    await userEvent.type(screen.getByLabelText('Bodega origen'), 'Prin{enter}')
    await userEvent.click(screen.getByLabelText('Bodega destino'))
    await userEvent.type(screen.getByLabelText('Bodega destino'), 'Secu{enter}')
    await userEvent.type(screen.getByLabelText('Cantidad'), '2')
    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Reposicion urgente')
    await userEvent.click(screen.getByRole('button', { name: 'Registrar traslado' }))

    expect(await screen.findByText('Error al registrar traslado')).toBeInTheDocument()
    expect(await screen.findByText('Stock insuficiente para Motosierra: disponible 1.00.')).toBeInTheDocument()
    expect(screen.queryByText(/BUSINESS_RULE_ERROR/)).not.toBeInTheDocument()
  })
})
