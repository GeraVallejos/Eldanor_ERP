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
    let auditoriaHits = 0

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
              stock_nuevo: '15.50',
              costo_unitario: '12000.00',
              valor_total: '60000.00',
              documento_tipo: 'COMPRA_RECEPCION',
              referencia: 'OC-001',
            },
          ],
        })
      }),
      http.get('*/movimientos-inventario/mov-1/auditoria/', async () => {
        auditoriaHits += 1
        return HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'audit-1',
              summary: 'Movimiento ENTRADA registrado para producto Tijera poda.',
              event_type: 'INVENTARIO_MOVIMIENTO_REGISTRADO',
              action_code: 'EDITAR',
              occurred_at: '2026-03-10T12:01:00Z',
              changes: {
                stock_bodega: ['10.00', '15.50'],
              },
            },
          ],
        })
      }),
    )

    renderWithProviders(<InventarioKardexPage />)

    const productoInput = await screen.findByLabelText('Producto')
    await userEvent.type(productoInput, 'Tijera')
    await userEvent.click(await screen.findByRole('button', { name: 'Tijera poda' }))

    const bodegaInput = screen.getByLabelText('Bodega')
    await userEvent.type(bodegaInput, 'Principal')
    await userEvent.click(await screen.findByRole('button', { name: 'Principal' }))

    await userEvent.selectOptions(screen.getByLabelText('Tipo'), 'ENTRADA')
    await userEvent.click(screen.getByLabelText('Guia de recepcion'))
    await userEvent.click(screen.getByLabelText('Factura de compra'))
    await userEvent.type(screen.getByPlaceholderText('Ej: GUIA 123, FACTURA 456, ANULACION'), 'OC-001')
    await userEvent.click(screen.getByRole('button', { name: 'Consultar' }))

    expect((await screen.findAllByText('Compra recepcion')).length).toBeGreaterThan(0)
    expect(screen.getByText('OC-001')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('15,5')).toBeInTheDocument()
    expect(screen.queryByText('5.00')).not.toBeInTheDocument()
    expect(screen.queryByText('10.00')).not.toBeInTheDocument()
    expect(screen.queryByText('15.50')).not.toBeInTheDocument()
    expect(await screen.findByText('Auditoria del movimiento')).toBeInTheDocument()
    expect(await screen.findByText(/Movimiento ENTRADA registrado/)).toBeInTheDocument()
    expect(await screen.findByText('10.00 -> 15.50')).toBeInTheDocument()
    expect(auditoriaHits).toBeGreaterThan(0)

    await waitFor(() => {
      expect(kardexParams).toMatchObject({
        producto_id: 'prod-1',
        bodega_id: 'bod-1',
        tipo: 'ENTRADA',
        documento_tipo: 'GUIA_RECEPCION,FACTURA_COMPRA',
        referencia: 'OC-001',
      })
    })
  })
})
