import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioReportesPage from '@/modules/inventario/pages/InventarioReportesPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioReportesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga reporte valorizado y permite agrupar por bodega', async () => {
    let analyticsParams = null

    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-1', nombre: 'Tijera poda' },
          { id: 'prod-2', nombre: 'Motosierra' },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.get('*/stocks/reconciliation/', async () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              producto_id: 'prod-2',
              producto_nombre: 'Motosierra',
              bodega_id: 'bod-1',
              bodega_nombre: 'Principal',
              stock_actual: 5,
              stock_snapshot: 4,
              valor_actual: 60000,
              valor_snapshot: 48000,
              ultimo_snapshot_en: '2026-03-27T12:00:00Z',
            },
          ],
        }),
      ),
      http.get('*/stocks/analytics/', async ({ request }) => {
        analyticsParams = Object.fromEntries(new URL(request.url).searchParams.entries())
        const groupBy = analyticsParams.group_by || 'producto'

        if (groupBy === 'bodega') {
          return HttpResponse.json({
            metrics: { registros: 1, stock_total: 15, valor_total: 180000 },
            totales: { stock_total: 15, valor_total: 180000 },
            top_valorizados: [{ bodega__nombre: 'Principal', stock_total: 15, valor_total: 180000 }],
            criticos: [],
            health: {
              productos_criticos: 0,
              reservas_activas: 1,
              unidades_reservadas: 2,
              bodegas_con_stock: 1,
              sin_snapshot: 0,
              descuadrados_snapshot: 0,
            },
            reconciliation: { count: 0, detail: [] },
            detalle: [{ bodega__nombre: 'Principal', stock_total: 15, valor_total: 180000 }],
          })
        }

        return HttpResponse.json({
          metrics: { registros: 2, stock_total: 15, valor_total: 180000 },
          totales: { stock_total: 15, valor_total: 180000 },
          top_valorizados: [{ producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000 }],
          criticos: [{ producto_id: 'prod-2', producto__nombre: 'Motosierra', faltante: 2 }],
          health: {
            productos_criticos: 1,
            reservas_activas: 2,
            unidades_reservadas: 4,
            bodegas_con_stock: 1,
            sin_snapshot: 0,
            descuadrados_snapshot: 1,
          },
          reconciliation: { count: 1, detail: [] },
          detalle: [
            { producto__nombre: 'Tijera poda', stock_total: 10, valor_total: 120000 },
            { producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000 },
          ],
        })
      }),
    )

    renderWithProviders(<InventarioReportesPage />)

    expect(await screen.findByRole('heading', { name: 'Reportes de inventario' })).toBeInTheDocument()
    expect((await screen.findAllByText('Motosierra')).length).toBeGreaterThan(0)
    expect(screen.getByText('Top valorizados')).toBeInTheDocument()
    expect(screen.getByText('Criticos por minimo')).toBeInTheDocument()
    expect(screen.getByText('Salud operativa')).toBeInTheDocument()
    expect(screen.getByText('Conciliacion de stock')).toBeInTheDocument()
    expect(screen.getByText('Diferencias contra ultimo snapshot')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Investigar en kardex' })).toHaveAttribute('href', expect.stringContaining('/inventario/kardex?'))
    expect(screen.getByRole('link', { name: 'Abrir ajuste' })).toHaveAttribute('href', expect.stringContaining('/inventario/ajustes?'))
    expect(screen.getByRole('button', { name: 'Actualizar' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver auditoria' })).toHaveAttribute('href', '/inventario/auditoria')

    await userEvent.selectOptions(screen.getByLabelText('Agrupar por'), 'bodega')
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }))

    await waitFor(() => {
      expect(analyticsParams).toMatchObject({ group_by: 'bodega' })
    })
    expect(screen.getByText('Reservas activas:')).toBeInTheDocument()
  })
})
