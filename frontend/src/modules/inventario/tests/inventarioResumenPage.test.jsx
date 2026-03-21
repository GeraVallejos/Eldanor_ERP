import { screen } from '@testing-library/react'
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

  it('carga panel de inventario con accesos a reportes y operacion', async () => {
    server.use(
      http.get('*/stocks/', async () =>
        HttpResponse.json([
          { id: 'st-1', producto: 'prod-1', bodega: 'bod-1', stock: '10.00' },
          { id: 'st-2', producto: 'prod-2', bodega: 'bod-1', stock: '5.00' },
        ]),
      ),
      http.get('*/stocks/criticos/', async () =>
        HttpResponse.json({
          count: 1,
          detalle: [
            {
              producto_id: 'prod-2',
              producto__nombre: 'Motosierra',
              producto__sku: 'MOT-01',
              producto__stock_minimo: 8,
              stock_total: 5,
              faltante: 3,
            },
          ],
        }),
      ),
      http.get('*/movimientos-inventario/resumen_operativo/', async () =>
        HttpResponse.json({
          total_movimientos: 4,
          entradas: 2,
          salidas: 2,
          ajustes: 1,
          traslados: 2,
          cantidad_entrada: 13,
          cantidad_salida: 5,
          neto_unidades: 8,
        }),
      ),
      http.get('*/stocks/resumen/', async () =>
        HttpResponse.json({
          totales: { stock_total: 15, valor_total: 180000 },
          detalle: [
            { producto__nombre: 'Tijera poda', stock_total: 10, valor_total: 120000 },
            { producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000 },
          ],
        }),
      ),
    )

    renderWithProviders(<InventarioResumenPage />)

    expect(await screen.findByRole('heading', { name: 'Resumen de inventario' })).toBeInTheDocument()
    expect(await screen.findByText('$ 180.000')).toBeInTheDocument()
    expect(await screen.findByText('Stock critico')).toBeInTheDocument()
    expect(await screen.findByText('Movimientos registrados')).toBeInTheDocument()
    expect(screen.getByText('Neto de unidades')).toBeInTheDocument()
    expect((await screen.findAllByText('Motosierra')).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Ir a reportes' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a kardex' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a ajustes' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a traslados' })).toBeInTheDocument()
  })
})
