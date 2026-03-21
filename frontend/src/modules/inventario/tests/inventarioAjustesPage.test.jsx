import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioAjustesPage from '@/modules/inventario/pages/InventarioAjustesPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioAjustesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('previsualiza y aplica un ajuste de inventario', async () => {
    let regularizacionPayload = null
    let previewPayload = null

    server.use(
      http.get('*/movimientos-inventario/', async () =>
        HttpResponse.json([
          {
            id: 'mov-10',
            documento_tipo: 'AJUSTE',
            producto_id: 'prod-2',
            bodega_id: 'bod-1',
            referencia: 'Conteo marzo',
            tipo: 'AJUSTE',
            cantidad: '2.00',
            creado_en: '2026-03-20T10:00:00Z',
          },
        ]),
      ),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-2', nombre: 'Motosierra' }])),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.post('*/movimientos-inventario/previsualizar_regularizacion/', async ({ request }) => {
        previewPayload = await request.json()
        return HttpResponse.json({
          producto_id: 'prod-2',
          producto_nombre: 'Motosierra',
          bodega_id: 'bod-1',
          stock_actual: 5,
          stock_objetivo: 7,
          diferencia: 2,
          reservado_total: 0,
          disponible_actual: 5,
          tipo_movimiento: 'ENTRADA',
          ajustable: true,
          warnings: [],
        })
      }),
      http.post('*/movimientos-inventario/regularizar/', async ({ request }) => {
        regularizacionPayload = await request.json()
        return HttpResponse.json({ id: 'mov-1' }, { status: 201 })
      }),
    )

    renderWithProviders(<InventarioAjustesPage />, {
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

    expect(await screen.findByRole('heading', { name: 'Ajustes de inventario' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Historial de ajustes' })).toBeInTheDocument()
    expect(await screen.findByText('Conteo marzo')).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Producto ajuste'))
    await userEvent.type(screen.getByLabelText('Producto ajuste'), 'Moto{enter}')
    await userEvent.click(screen.getByLabelText('Bodega ajuste'))
    await userEvent.type(screen.getByLabelText('Bodega ajuste'), 'Prin{enter}')
    await userEvent.type(screen.getByLabelText('Stock contado'), '7')
    await userEvent.click(screen.getByRole('button', { name: 'Previsualizar' }))

    await waitFor(() => {
      expect(previewPayload).toMatchObject({
        producto_id: 'prod-2',
        bodega_id: 'bod-1',
        stock_objetivo: '7',
      })
    })

    await userEvent.click(screen.getByRole('button', { name: 'Aplicar ajuste' }))

    await waitFor(() => {
      expect(regularizacionPayload).toMatchObject({
        producto_id: 'prod-2',
        bodega_id: 'bod-1',
        stock_objetivo: '7',
        referencia: 'Conteo fisico Motosierra',
      })
    })

    await userEvent.type(screen.getByLabelText('Buscar referencia'), 'marzo')
    expect(screen.getByDisplayValue('marzo')).toBeInTheDocument()
  })
})
