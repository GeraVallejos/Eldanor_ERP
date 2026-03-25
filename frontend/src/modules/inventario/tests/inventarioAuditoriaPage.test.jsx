import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioAuditoriaPage from '@/modules/inventario/pages/InventarioAuditoriaPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioAuditoriaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('consulta historial auditado con filtros y muestra detalle del evento', async () => {
    let historialParams = null

    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-1', nombre: 'Tijera poda', tipo: 'PRODUCTO' },
          { id: 'prod-2', nombre: 'Motosierra', tipo: 'PRODUCTO' },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.get('*/movimientos-inventario/historial/', async ({ request }) => {
        historialParams = Object.fromEntries(new URL(request.url).searchParams.entries())
        return HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'audit-1',
              entity_id: 'mov-1',
              entity_type: 'MOVIMIENTO_INVENTARIO',
              action_code: 'EDITAR',
              event_type: 'INVENTARIO_MOVIMIENTO_REGISTRADO',
              occurred_at: '2026-03-21T10:00:00Z',
              summary: 'Movimiento ENTRADA registrado para producto Tijera poda.',
              changes: {
                stock_bodega: ['10.00', '15.00'],
              },
              payload: {
                producto_id: 'prod-1',
                bodega_id: 'bod-1',
                documento_tipo: 'AJUSTE',
                tipo: 'ENTRADA',
              },
              meta: {
                source: 'InventarioService.registrar_movimiento',
              },
            },
          ],
        })
      }),
    )

    renderWithProviders(<InventarioAuditoriaPage />)

    expect(await screen.findByRole('heading', { name: 'Auditoria de inventario' })).toBeInTheDocument()
    expect(await screen.findByText('Historial de eventos')).toBeInTheDocument()

    await userEvent.click(screen.getByLabelText('Producto auditoria'))
    await userEvent.type(screen.getByLabelText('Producto auditoria'), 'Tijera{enter}')
    await userEvent.click(screen.getByLabelText('Bodega auditoria'))
    await userEvent.type(screen.getByLabelText('Bodega auditoria'), 'Principal{enter}')
    await userEvent.selectOptions(screen.getByLabelText('Documento'), 'AJUSTE')
    await userEvent.selectOptions(screen.getByLabelText('Tipo de movimiento'), 'ENTRADA')
    await userEvent.type(screen.getByPlaceholderText('Documento, motivo, observacion o referencia...'), 'Tijera')
    await userEvent.click(screen.getByRole('button', { name: 'Consultar' }))

    expect((await screen.findAllByText(/Movimiento ENTRADA registrado/)).length).toBeGreaterThan(0)
    expect(await screen.findByText('stock_bodega')).toBeInTheDocument()
    expect(await screen.findByText('10.00 -> 15.00')).toBeInTheDocument()
    expect(await screen.findByText(/InventarioService\.registrar_movimiento/)).toBeInTheDocument()

    await waitFor(() => {
      expect(historialParams).toMatchObject({
        producto_id: 'prod-1',
        bodega_id: 'bod-1',
        documento_tipo: 'AJUSTE',
        tipo: 'ENTRADA',
        referencia: 'Tijera',
      })
    })
  })
})
