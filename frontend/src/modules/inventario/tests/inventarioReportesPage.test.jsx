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
      http.get('*/stocks/analytics/', async ({ request }) => {
        analyticsParams = Object.fromEntries(new URL(request.url).searchParams.entries())
        const groupBy = analyticsParams.group_by || 'producto'

        if (groupBy === 'bodega') {
          return HttpResponse.json({
            metrics: { registros: 1, stock_total: 15, valor_total: 180000 },
            totales: { stock_total: 15, valor_total: 180000 },
            top_valorizados: [{ bodega__nombre: 'Principal', stock_total: 15, valor_total: 180000 }],
            criticos: [],
            detalle: [{ bodega__nombre: 'Principal', stock_total: 15, valor_total: 180000 }],
          })
        }

        return HttpResponse.json({
          metrics: { registros: 2, stock_total: 15, valor_total: 180000 },
          totales: { stock_total: 15, valor_total: 180000 },
          top_valorizados: [{ producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000 }],
          criticos: [{ producto_id: 'prod-2', producto__nombre: 'Motosierra', faltante: 2 }],
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
    expect(screen.getByRole('button', { name: 'Actualizar' })).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Agrupar por'), 'bodega')
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }))

    await waitFor(() => {
      expect(analyticsParams).toMatchObject({ group_by: 'bodega' })
    })
  })
})
