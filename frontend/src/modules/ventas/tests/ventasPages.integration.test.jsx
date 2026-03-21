import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VentasPedidosListPage from '@/modules/ventas/pages/VentasPedidosListPage'
import VentasFacturasListPage from '@/modules/ventas/pages/VentasFacturasListPage'
import VentasNotasListPage from '@/modules/ventas/pages/VentasNotasListPage'
import VentasResumenPage from '@/modules/ventas/pages/VentasResumenPage'
import VentasReportesPage from '@/modules/ventas/pages/VentasReportesPage'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { server } from '@/test/msw/server'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

function authState(permissions = ['VENTAS.VER']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'ventas@eldanor.cl',
        permissions,
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
  }
}

describe('ventas/pages integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('permite confirmar pedido desde listado cuando tiene permiso', async () => {
    server.use(
      http.get('*/pedidos-venta/', async () =>
        HttpResponse.json([
          {
            id: 'ped-1',
            numero: 'PV-001',
            estado: 'BORRADOR',
            fecha_emision: '2026-03-19',
            total: 119000,
          },
        ]),
      ),
      http.post('*/pedidos-venta/ped-1/confirmar/', async () =>
        HttpResponse.json({ id: 'ped-1', estado: 'CONFIRMADO' }),
      ),
    )

    renderWithProviders(<VentasPedidosListPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.APROBAR', 'VENTAS.EDITAR', 'VENTAS.CREAR', 'VENTAS.ANULAR']),
    })

    expect(await screen.findByText('PV-001')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Pedido actualizado correctamente.')
    })
  })

  it('oculta acciones de pedidos cuando solo tiene permiso de lectura', async () => {
    server.use(
      http.get('*/pedidos-venta/', async () =>
        HttpResponse.json([
          {
            id: 'ped-2',
            numero: 'PV-002',
            estado: 'BORRADOR',
            fecha_emision: '2026-03-19',
            total: 50000,
          },
        ]),
      ),
    )

    renderWithProviders(<VentasPedidosListPage />, {
      preloadedState: authState(['VENTAS.VER']),
    })

    expect(await screen.findByText('PV-002')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nuevo pedido' })).not.toBeInTheDocument()
  })

  it('permite emitir factura desde listado con permiso de aprobar', async () => {
    server.use(
      http.get('*/facturas-venta/', async () =>
        HttpResponse.json([
          {
            id: 'fac-1',
            numero: 'FV-001',
            estado: 'BORRADOR',
            fecha_emision: '2026-03-19',
            total: 23800,
          },
        ]),
      ),
      http.post('*/facturas-venta/fac-1/emitir/', async () =>
        HttpResponse.json({ id: 'fac-1', estado: 'EMITIDA' }),
      ),
    )

    renderWithProviders(<VentasFacturasListPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.APROBAR', 'VENTAS.EDITAR', 'VENTAS.CREAR']),
    })

    expect(await screen.findByText('FV-001')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver resumen' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver reportes' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Emitir' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Factura actualizada.')
    })
  })

  it('oculta editar y confirmar cuando el pedido ya no esta en borrador', async () => {
    server.use(
      http.get('*/pedidos-venta/', async () =>
        HttpResponse.json([
          {
            id: 'ped-3',
            numero: 'PV-003',
            estado: 'DESPACHADO',
            fecha_emision: '2026-03-19',
            total: 65000,
          },
        ]),
      ),
      http.get('*/facturas-venta-items/', async () =>
        HttpResponse.json([
          { id: 'fi-1', factura_venta: 'fac-1', producto: 'prod-1', descripcion: 'Consulta general', cantidad: 2, precio_unitario: 50000 },
          { id: 'fi-2', factura_venta: 'fac-2', producto: 'prod-2', descripcion: 'Vacuna octuple', cantidad: 1, precio_unitario: 88000 },
        ]),
      ),
    )

    renderWithProviders(<VentasPedidosListPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.APROBAR', 'VENTAS.EDITAR', 'VENTAS.ANULAR']),
    })

    expect(await screen.findByText('PV-003')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Confirmar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Anular' })).not.toBeInTheDocument()
  })

  it('oculta editar de factura emitida aunque el usuario tenga permiso', async () => {
    server.use(
      http.get('*/facturas-venta/resumen_operativo/', async () =>
        HttpResponse.json({
          total_documentos: 1,
          monto_total: 45000,
          monto_emitido: 45000,
          monto_vencido: 45000,
          monto_por_vencer_7_dias: 45000,
          borradores: 0,
          emitidas: 1,
          anuladas: 0,
          vencidas: 0,
          por_vencer_7_dias: 1,
        }),
      ),
      http.get('*/facturas-venta/', async () =>
        HttpResponse.json([
          {
            id: 'fac-2',
            numero: 'FV-002',
            estado: 'EMITIDA',
            fecha_emision: '2026-03-19',
            total: 45000,
          },
        ]),
      ),
    )

    renderWithProviders(<VentasFacturasListPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.APROBAR', 'VENTAS.EDITAR', 'VENTAS.ANULAR']),
    })

    expect(await screen.findByText('FV-002')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Emitir' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anular' })).toBeInTheDocument()
  })

  it('permite anular nota emitida cuando tiene permiso anular', async () => {
    server.use(
      http.get('*/notas-credito-venta/', async () =>
        HttpResponse.json([
          {
            id: 'nc-1',
            numero: 'NC-001',
            estado: 'EMITIDA',
            fecha_emision: '2026-03-19',
            total: 11900,
          },
        ]),
      ),
      http.post('*/notas-credito-venta/nc-1/anular/', async () =>
        HttpResponse.json({ id: 'nc-1', estado: 'ANULADA' }),
      ),
    )

    renderWithProviders(<VentasNotasListPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.ANULAR', 'VENTAS.EDITAR']),
    })

    expect(await screen.findByText('NC-001')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Anular' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Nota de credito actualizada.')
    })
  })

  it('muestra resumen operativo de facturas en el resumen de ventas', async () => {
    server.use(
      http.get('*/facturas-venta/resumen_operativo/', async () =>
        HttpResponse.json({
          total_documentos: 4,
          monto_total: 238000,
          monto_emitido: 200000,
          monto_vencido: 45000,
          monto_por_vencer_7_dias: 20000,
          borradores: 1,
          emitidas: 2,
          anuladas: 1,
          vencidas: 1,
          por_vencer_7_dias: 1,
        }),
      ),
    )

    renderWithProviders(<VentasResumenPage />, {
      preloadedState: authState(['VENTAS.VER']),
    })

    expect(await screen.findByText('Facturacion total')).toBeInTheDocument()
    expect(screen.getByText(/\$?\s*238\.000/)).toBeInTheDocument()
    expect(screen.getByText('Cartera a vigilar')).toBeInTheDocument()
    expect(screen.getByText(/\$?\s*45\.000/)).toBeInTheDocument()
  })

  it('muestra reportes exportables de facturacion y cartera', async () => {
    const analyticsBase = {
      filters: { agrupacion: 'mensual' },
      metrics: {
        total_facturas: 2,
        facturacion_total: 238000,
        monto_emitido: 150000,
        emitidas: 1,
        borradores: 1,
        anuladas: 0,
        vencidas: 1,
        monto_vencido: 150000,
        por_vencer: 0,
        monto_por_vencer: 0,
      },
      top_clientes: [{ cliente_id: 'cli-1', nombre: 'Clinica Norte', total: 150000 }],
      top_productos: [{ producto_id: 'prod-1', nombre: 'Consulta general', cantidad: 2, monto: 100000 }],
      series: [{ periodo: '2026-03-01', cantidad: 2, monto: 238000 }],
      documentos_vencidos: [
        { id: 'fac-1', numero: 'FV-001', cliente_nombre: 'Clinica Norte', fecha_vencimiento: '2026-03-15', total: 150000 },
      ],
      detail: [
        { id: 'fac-1', numero: 'FV-001', cliente_id: 'cli-1', cliente_nombre: 'Clinica Norte', fecha_emision: '2026-03-10', fecha_vencimiento: '2026-03-15', estado: 'EMITIDA', total: 150000 },
        { id: 'fac-2', numero: 'FV-002', cliente_id: 'cli-2', cliente_nombre: 'Clinica Sur', fecha_emision: '2026-03-18', fecha_vencimiento: '2026-03-25', estado: 'BORRADOR', total: 88000 },
      ],
    }
    const analyticsFiltrado = {
      filters: { agrupacion: 'semanal' },
      metrics: {
        total_facturas: 1,
        facturacion_total: 88000,
        monto_emitido: 0,
        emitidas: 0,
        borradores: 1,
        anuladas: 0,
        vencidas: 0,
        monto_vencido: 0,
        por_vencer: 0,
        monto_por_vencer: 0,
      },
      top_clientes: [{ cliente_id: 'cli-2', nombre: 'Clinica Sur', total: 88000 }],
      top_productos: [{ producto_id: 'prod-2', nombre: 'Vacuna octuple', cantidad: 1, monto: 88000 }],
      series: [{ periodo: '2026-W12', cantidad: 1, monto: 88000 }],
      documentos_vencidos: [],
      detail: [
        { id: 'fac-2', numero: 'FV-002', cliente_id: 'cli-2', cliente_nombre: 'Clinica Sur', fecha_emision: '2026-03-18', fecha_vencimiento: '2026-03-25', estado: 'BORRADOR', total: 88000 },
      ],
    }

    server.use(
      http.get('*/facturas-venta/analytics/', async ({ request }) => {
        const url = new URL(request.url)
        const estado = url.searchParams.get('estado')
        const agrupacion = url.searchParams.get('agrupacion')
        if (estado === 'BORRADOR' && agrupacion === 'semanal') {
          return HttpResponse.json(analyticsFiltrado)
        }
        return HttpResponse.json(analyticsBase)
      }),
    )

    renderWithProviders(<VentasReportesPage />, {
      preloadedState: authState(['VENTAS.VER']),
    })

    expect(await screen.findByText('Reporte comercial')).toBeInTheDocument()
    expect(screen.getByLabelText('Cliente')).toBeInTheDocument()
    expect(screen.getByText('Facturacion total')).toBeInTheDocument()
    expect(screen.getByText('Top clientes por monto')).toBeInTheDocument()
    expect(screen.getByText('Top productos vendidos')).toBeInTheDocument()
    expect(screen.getByText('Reporte de cartera')).toBeInTheDocument()
    expect(screen.getByText('Tendencia mensual')).toBeInTheDocument()
    expect(screen.getByText('Documentos vencidos a vigilar')).toBeInTheDocument()
    expect(screen.getByText('Clinica Norte')).toBeInTheDocument()
    expect(screen.getByText('FV-001')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'BORRADOR')
    await userEvent.selectOptions(screen.getByLabelText('Agrupacion temporal'), 'semanal')

    await waitFor(() => {
      expect(screen.getByText('Tendencia semanal')).toBeInTheDocument()
    })
    expect(screen.queryByText('FV-001')).not.toBeInTheDocument()
    expect(screen.getByText('FV-002')).toBeInTheDocument()
    expect(screen.getByText('Clinica Sur')).toBeInTheDocument()
  })
})
