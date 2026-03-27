import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InventarioReportesPage from '@/modules/inventario/pages/InventarioReportesPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

vi.mock('@/modules/shared/exports/downloadExcelFile', () => ({
  downloadExcelFile: vi.fn(),
}))

describe('inventario/InventarioReportesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    invalidateProductosCatalogCache()
  })

  it('carga reporte valorizado y permite agrupar por bodega', async () => {
    let analyticsParams = null

    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-1', nombre: 'Tijera poda', sku: 'TIJ-001', tipo: 'PRODUCTO', usa_lotes: false, usa_vencimiento: false, usa_series: false },
          { id: 'prod-2', nombre: 'Motosierra', sku: 'MOT-001', tipo: 'PRODUCTO', usa_lotes: true, usa_vencimiento: true, usa_series: false },
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
      http.get('*/cortes-inventario/', async () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'corte-1',
              numero: 'CIN-0001',
              estado: 'GENERADO',
              fecha_corte: '2026-03-27',
              observaciones: 'Cierre diario',
              subtotal: 15,
              total: 180000,
              reservado_total: 4,
              disponible_total: 11,
              items_count: 2,
              creado_en: '2026-03-27T13:00:00Z',
              actualizado_en: '2026-03-27T13:00:00Z',
            },
          ],
        }),
      ),
      http.get('*/cortes-inventario/corte-1/items/', async () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'corte-item-1',
              producto: 'prod-2',
              bodega: 'bod-1',
              producto_nombre: 'Motosierra',
              producto_sku: 'MOT-001',
              producto_categoria_nombre: 'Herramientas',
              bodega_nombre: 'Principal',
              stock: 5,
              reservado: 1,
              disponible: 4,
              costo_promedio: 12000,
              valor_stock: 60000,
              lotes_activos: 'LT-001',
              proximo_vencimiento: '2027-10-31',
              series_disponibles: 0,
              series_muestra: '',
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
          top_valorizados: [{ producto_id: 'prod-2', producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000, lotes_activos: 'LT-001', proximo_vencimiento: '2027-10-31', series_disponibles: 0 }],
          criticos: [{ producto_id: 'prod-2', producto__nombre: 'Motosierra', faltante: 2, lotes_activos: 'LT-001', proximo_vencimiento: '2027-10-31', series_disponibles: 0 }],
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
            { producto_id: 'prod-1', producto__nombre: 'Tijera poda', stock_total: 10, valor_total: 120000, lotes_activos: '-', proximo_vencimiento: null, series_disponibles: 0, series_muestra: '-' },
            { producto_id: 'prod-2', producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000, lotes_activos: 'LT-001', proximo_vencimiento: '2027-10-31', series_disponibles: 0, series_muestra: '-' },
          ],
        })
      }),
    )

    renderWithProviders(<InventarioReportesPage />)

    expect(await screen.findByRole('heading', { name: 'Reportes de inventario' })).toBeInTheDocument()
    expect((await screen.findAllByText('Motosierra')).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Lotes: LT-001/).length).toBeGreaterThan(0)
    expect(screen.getByText('31/10/2027')).toBeInTheDocument()
    expect(screen.getByText('Top valorizados')).toBeInTheDocument()
    expect(screen.getByText('Criticos por minimo')).toBeInTheDocument()
    expect(screen.getByText('Salud operativa')).toBeInTheDocument()
    expect(screen.getByText('Conciliacion de stock')).toBeInTheDocument()
    expect(screen.getByText('Diferencias contra ultimo snapshot')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Investigar en kardex' })).toHaveAttribute('href', expect.stringContaining('/inventario/kardex?'))
    expect(screen.getByRole('link', { name: 'Abrir ajuste' })).toHaveAttribute('href', expect.stringContaining('/inventario/ajustes?'))
    expect(screen.getAllByRole('button', { name: 'Actualizar' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Ver auditoria' })).toHaveAttribute('href', '/inventario/auditoria')
    expect(screen.getByRole('button', { name: 'Ver cortes y cierres' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Ver cortes y cierres' }))
    expect(screen.getByText('Snapshot completo del inventario')).toBeInTheDocument()
    expect(screen.getByText('CIN-0001')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Agrupar por'), 'bodega')
    await userEvent.click(screen.getAllByRole('button', { name: 'Actualizar' })[0])

    await waitFor(() => {
      expect(analyticsParams).toMatchObject({ group_by: 'bodega' })
    })
    expect(screen.getByText('Reservas activas:')).toBeInTheDocument()
  })

  it('exporta excel por producto sin columnas tecnicas y con trazabilidad', async () => {
    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-2', nombre: 'Motosierra', sku: 'MOT-001', tipo: 'PRODUCTO', usa_lotes: true, usa_vencimiento: true, usa_series: true },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.get('*/stocks/reconciliation/', async () =>
        HttpResponse.json({ count: 0, next: null, previous: null, results: [] }),
      ),
      http.get('*/cortes-inventario/', async () =>
        HttpResponse.json({ count: 0, next: null, previous: null, results: [] }),
      ),
      http.get('*/stocks/analytics/', async () =>
        HttpResponse.json({
          metrics: { registros: 1, stock_total: 5, valor_total: 60000 },
          totales: { stock_total: 5, valor_total: 60000 },
          top_valorizados: [{ producto__nombre: 'Motosierra', stock_total: 5, valor_total: 60000 }],
          criticos: [],
          health: {
            productos_criticos: 0,
            reservas_activas: 0,
            unidades_reservadas: 0,
            bodegas_con_stock: 1,
            sin_snapshot: 0,
            descuadrados_snapshot: 0,
          },
          reconciliation: { count: 0, detail: [] },
          detalle: [
            {
              producto_id: 'prod-2',
              producto__nombre: 'Motosierra',
              producto__categoria__nombre: 'Herramientas',
              lotes_activos: 'LT-001, LT-002',
              proximo_vencimiento: '2027-10-31',
              series_disponibles: 3,
              series_muestra: 'SR-001, SR-002, SR-003',
              stock_total: 5,
              reservado_total: 1,
              disponible_total: 4,
              valor_total: 60000,
            },
          ],
        }),
      ),
    )

    renderWithProviders(<InventarioReportesPage />)

    expect(await screen.findByRole('heading', { name: 'Reportes de inventario' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Exportar' }))
    await userEvent.click(screen.getByRole('button', { name: 'Exportar Excel' }))

    await waitFor(() => {
      expect(downloadExcelFile).toHaveBeenCalled()
    })

    const payload = vi.mocked(downloadExcelFile).mock.calls[0][0]
    expect(payload.columns.map((column) => column.header)).toEqual(
      expect.arrayContaining(['Lotes activos', 'Proximo vencimiento', 'Series disponibles', 'Muestra series']),
    )
    expect(payload.columns.map((column) => column.header)).not.toEqual(
      expect.arrayContaining(['Agrupacion', 'Filtro producto', 'Filtro bodega', 'Solo con stock', 'Usa lotes', 'Usa vencimiento', 'Usa series']),
    )
    expect(payload.rows).toHaveLength(1)
    expect(payload.rows[0].grupo).toBe('Motosierra')
    expect(payload.rows[0].sku).toBe('MOT-001')
    expect(payload.rows[0].lotes_activos).toBe('LT-001, LT-002')
    expect(payload.rows[0].proximo_vencimiento).toBe('31/10/2027')
    expect(payload.rows[0].series_disponibles).toBe(3)
    expect(payload.rows[0].series_muestra).toBe('SR-001, SR-002, SR-003')
  })
})
