import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioResumenPage from '@/modules/inventario/pages/InventarioResumenPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('inventario/InventarioResumenPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga resumen valorizado y permite agrupar por bodega', async () => {
    let resumenParams = null

    server.use(
      http.get('*/stocks/', async () =>
        HttpResponse.json([
          { id: 'st-1', producto: 'prod-1', bodega: 'bod-1', stock: '10.00' },
          { id: 'st-2', producto: 'prod-2', bodega: 'bod-1', stock: '5.00' },
        ]),
      ),
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-1', nombre: 'Tijera poda' },
          { id: 'prod-2', nombre: 'Motosierra' },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.get('*/stocks/resumen/', async ({ request }) => {
        resumenParams = Object.fromEntries(new URL(request.url).searchParams.entries())
        const groupBy = resumenParams.group_by || 'producto'

        if (groupBy === 'bodega') {
          return HttpResponse.json({
            totales: { stock_total: 15, valor_total: 180000 },
            detalle: [{ bodega__nombre: 'Principal', stock_total: 15, valor_total: 180000 }],
          })
        }

        return HttpResponse.json({
          totales: { stock_total: 15, valor_total: 180000 },
          detalle: [
            { producto__nombre: 'Tijera poda', stock_total: 10, valor_total: 120000 },
            { producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000 },
          ],
        })
      }),
    )

    renderWithProviders(<InventarioResumenPage />)

    expect(await screen.findByRole('heading', { name: 'Resumen valorizado' })).toBeInTheDocument()
    expect(await screen.findByText('$ 180.000')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Agrupar por'), 'bodega')
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }))

    await waitFor(() => {
      expect(resumenParams).toMatchObject({ group_by: 'bodega' })
    })

    const principalMatches = await screen.findAllByText('Principal')
    expect(principalMatches.length).toBeGreaterThanOrEqual(1)
  })
})
