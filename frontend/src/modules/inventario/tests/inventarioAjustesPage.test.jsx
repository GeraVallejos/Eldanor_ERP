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

    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Conteo ciclico')
    await userEvent.type(screen.getByLabelText('Referencia operativa'), 'ACTA-2026-03')
    await userEvent.type(screen.getByLabelText('Observaciones'), 'Diferencia detectada en rack A1')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar ajuste' }))

    await waitFor(() => {
      expect(regularizacionPayload).toMatchObject({
        producto_id: 'prod-2',
        bodega_id: 'bod-1',
        stock_objetivo: '7',
        referencia: 'Conteo ciclico | ACTA-2026-03 | Diferencia detectada en rack A1',
      })
    })

  })

  it('envia lote y vencimiento cuando el producto usa trazabilidad por lote', async () => {
    let regularizacionPayload = null

    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-lote', nombre: 'Pintura industrial', usa_lotes: true, usa_vencimiento: true },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.post('*/movimientos-inventario/previsualizar_regularizacion/', async () =>
        HttpResponse.json({
          producto_id: 'prod-lote',
          producto_nombre: 'Pintura industrial',
          bodega_id: 'bod-1',
          stock_actual: 5,
          stock_objetivo: 7,
          diferencia: 2,
          reservado_total: 0,
          disponible_actual: 5,
          tipo_movimiento: 'ENTRADA',
          ajustable: true,
          warnings: [],
        }),
      ),
      http.post('*/movimientos-inventario/regularizar/', async ({ request }) => {
        regularizacionPayload = await request.json()
        return HttpResponse.json({ id: 'mov-lote' }, { status: 201 })
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

    await screen.findByRole('heading', { name: 'Ajustes de inventario' })
    await userEvent.click(screen.getByLabelText('Producto ajuste'))
    await userEvent.type(screen.getByLabelText('Producto ajuste'), 'Pint{enter}')
    await userEvent.click(screen.getByLabelText('Bodega ajuste'))
    await userEvent.type(screen.getByLabelText('Bodega ajuste'), 'Prin{enter}')
    await userEvent.type(screen.getByLabelText('Stock contado'), '7')
    await userEvent.click(screen.getByRole('button', { name: 'Previsualizar' }))
    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Conteo por lote')
    await userEvent.type(screen.getByLabelText('Lote'), 'lt-2026-01')
    await userEvent.type(screen.getByLabelText('Fecha de vencimiento'), '2026-12-31')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar ajuste' }))

    await waitFor(() => {
      expect(regularizacionPayload).toMatchObject({
        producto_id: 'prod-lote',
        lote_codigo: 'LT-2026-01',
        fecha_vencimiento: '2026-12-31',
      })
    })
  })

  it('bloquea el ajuste si el producto requiere lote y no se informa', async () => {
    server.use(
      http.get('*/productos/', async () =>
        HttpResponse.json([
          { id: 'prod-lote', nombre: 'Pintura industrial', usa_lotes: true, usa_vencimiento: false },
        ]),
      ),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.post('*/movimientos-inventario/previsualizar_regularizacion/', async () =>
        HttpResponse.json({
          producto_id: 'prod-lote',
          producto_nombre: 'Pintura industrial',
          bodega_id: 'bod-1',
          stock_actual: 5,
          stock_objetivo: 7,
          diferencia: 2,
          reservado_total: 0,
          disponible_actual: 5,
          tipo_movimiento: 'ENTRADA',
          ajustable: true,
          warnings: [],
        }),
      ),
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

    await screen.findByRole('heading', { name: 'Ajustes de inventario' })
    await userEvent.click(screen.getByLabelText('Producto ajuste'))
    await userEvent.type(screen.getByLabelText('Producto ajuste'), 'Pint{enter}')
    await userEvent.click(screen.getByLabelText('Bodega ajuste'))
    await userEvent.type(screen.getByLabelText('Bodega ajuste'), 'Prin{enter}')
    await userEvent.type(screen.getByLabelText('Stock contado'), '7')
    await userEvent.click(screen.getByRole('button', { name: 'Previsualizar' }))
    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Conteo por lote')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar ajuste' }))

    expect(await screen.findByText('Error al aplicar ajuste')).toBeInTheDocument()
    expect(await screen.findByText('Debe indicar el lote para ajustar este producto.')).toBeInTheDocument()
  })

  it('muestra error del contrato API al aplicar un ajuste', async () => {
    server.use(
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-2', nombre: 'Motosierra' }])),
      http.get('*/bodegas/', async () => HttpResponse.json([{ id: 'bod-1', nombre: 'Principal' }])),
      http.post('*/movimientos-inventario/previsualizar_regularizacion/', async () =>
        HttpResponse.json({
          producto_id: 'prod-2',
          producto_nombre: 'Motosierra',
          bodega_id: 'bod-1',
          stock_actual: 5,
          stock_objetivo: 3,
          diferencia: -2,
          reservado_total: 4,
          disponible_actual: 1,
          tipo_movimiento: 'SALIDA',
          ajustable: true,
          warnings: [],
        }),
      ),
      http.post('*/movimientos-inventario/regularizar/', async () =>
        HttpResponse.json(
          {
            detail: 'No se puede regularizar por debajo del stock reservado en la bodega.',
            error_code: 'BUSINESS_RULE_ERROR',
          },
          { status: 400 },
        ),
      ),
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

    await screen.findByRole('heading', { name: 'Ajustes de inventario' })
    await userEvent.click(screen.getByLabelText('Producto ajuste'))
    await userEvent.type(screen.getByLabelText('Producto ajuste'), 'Moto{enter}')
    await userEvent.click(screen.getByLabelText('Bodega ajuste'))
    await userEvent.type(screen.getByLabelText('Bodega ajuste'), 'Prin{enter}')
    await userEvent.type(screen.getByLabelText('Stock contado'), '3')
    await userEvent.click(screen.getByRole('button', { name: 'Previsualizar' }))
    await userEvent.type(screen.getByLabelText('Motivo operativo'), 'Merma')
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar ajuste' }))

    expect(await screen.findByText('Error al aplicar ajuste')).toBeInTheDocument()
    expect(await screen.findByText('No se puede regularizar por debajo del stock reservado en la bodega.')).toBeInTheDocument()
    expect(screen.queryByText(/BUSINESS_RULE_ERROR/)).not.toBeInTheDocument()
  })
})
