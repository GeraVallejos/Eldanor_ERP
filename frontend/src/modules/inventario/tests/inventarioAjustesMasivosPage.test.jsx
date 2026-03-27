import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioAjustesMasivosPage from '@/modules/inventario/pages/InventarioAjustesMasivosPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioAjustesMasivosPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('envia lote y vencimiento en lineas de ajuste masivo', async () => {
    let createPayload = null
    const createdDocument = {
      id: 'ajm-1',
      numero: 'AJM-0001',
      estado: 'BORRADOR',
      referencia: 'CONTEO POR LOTE | ACTA-2026',
      motivo: 'CONTEO POR LOTE',
      observaciones: '',
      items: [
        {
          id: 'item-1',
          producto: 'prod-lote',
          producto_nombre: 'Pintura industrial',
          bodega: 'bod-1',
          bodega_nombre: 'Principal',
          stock_actual: '0.00',
          stock_objetivo: '7.00',
          lote_codigo: 'LT-2026-01',
          fecha_vencimiento: '2026-12-31',
          diferencia: '0.00',
          movimiento: null,
        },
      ],
    }

    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-lote', nombre: 'Pintura industrial', usa_lotes: true, usa_vencimiento: true },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.get('*/ajustes-masivos/', async () => HttpResponse.json({ count: 0, results: [] })),
      http.get('*/ajustes-masivos/ajm-1/', async () => HttpResponse.json(createdDocument)),
      http.post('*/ajustes-masivos/', async ({ request }) => {
        createPayload = await request.json()
        return HttpResponse.json(createdDocument, { status: 201 })
      }),
    )

    const { container } = renderWithProviders(<InventarioAjustesMasivosPage />)

    expect(await screen.findByRole('heading', { name: 'Ajuste masivo de inventario' })).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Producto ajuste masivo 1'))
    await userEvent.type(screen.getByLabelText('Producto ajuste masivo 1'), 'Pint{enter}')
    await userEvent.click(screen.getByLabelText('Bodega ajuste masivo 1'))
    await userEvent.type(screen.getByLabelText('Bodega ajuste masivo 1'), 'Prin{enter}')
    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Conteo por lote')
    await userEvent.type(container.querySelector('input[type="number"]'), '7')
    await userEvent.type(screen.getByPlaceholderText('Segun producto'), 'lt-2026-01')
    await userEvent.type(container.querySelector('input[type="date"]'), '2026-12-31')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar borrador' }))

    await waitFor(() => {
      expect(createPayload).toMatchObject({
        estado: 'BORRADOR',
        motivo: 'Conteo por lote',
        items: [
          {
            producto_id: 'prod-lote',
            bodega_id: 'bod-1',
            stock_objetivo: '7',
            lote_codigo: 'LT-2026-01',
            fecha_vencimiento: '2026-12-31',
          },
        ],
      })
    })
    expect(await screen.findByText(/AJM-0001 \| BORRADOR/)).toBeInTheDocument()
  })
})
