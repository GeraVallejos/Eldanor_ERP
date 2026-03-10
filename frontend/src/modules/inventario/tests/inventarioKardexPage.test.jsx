import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioKardexPage from '@/modules/inventario/pages/InventarioKardexPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioKardexPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('consulta kardex con filtros y renderiza filas', async () => {
    let kardexParams = null

    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-1', nombre: 'Tijera poda', tipo: 'PRODUCTO' },
          { id: 'prod-2', nombre: 'Motosierra', tipo: 'PRODUCTO' },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.get('*/movimientos-inventario/kardex/', async ({ request }) => {
        kardexParams = Object.fromEntries(new URL(request.url).searchParams.entries())
        return HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'mov-1',
              creado_en: '2026-03-10T12:00:00Z',
              tipo: 'ENTRADA',
              cantidad: '5.00',
              stock_anterior: '10.00',
              stock_nuevo: '15.00',
              costo_unitario: '12000.00',
              valor_total: '60000.00',
              documento_tipo: 'COMPRA_RECEPCION',
              referencia: 'OC-001',
            },
          ],
        })
      }),
    )

    renderWithProviders(<InventarioKardexPage />)

    await userEvent.selectOptions(await screen.findByLabelText('Producto'), 'prod-1')
    await userEvent.selectOptions(screen.getByLabelText('Bodega'), 'bod-1')
    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'ENTRADA')
    await userEvent.type(screen.getByPlaceholderText('Buscar texto de referencia'), 'OC-001')
    await userEvent.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByText('COMPRA_RECEPCION')).toBeInTheDocument()
    expect(screen.getByText('OC-001')).toBeInTheDocument()

    await waitFor(() => {
      expect(kardexParams).toMatchObject({
        producto_id: 'prod-1',
        bodega_id: 'bod-1',
        tipo: 'ENTRADA',
        referencia: 'OC-001',
      })
    })
  })
})
