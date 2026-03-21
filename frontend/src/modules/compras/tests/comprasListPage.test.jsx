import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ComprasOrdenesListPage from '@/modules/compras/pages/ComprasOrdenesListPage'
import ComprasResumenPage from '@/modules/compras/pages/ComprasResumenPage'
import ComprasReportesPage from '@/modules/compras/pages/ComprasReportesPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

function authState(permissions = ['COMPRAS.VER']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'compras@eldanor.cl',
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

describe('compras/ListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lista registros y permite filtrar/buscar', async () => {
    server.use(
      http.get('*/ordenes-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_ordenes: 2,
          monto_total: 35000,
          borrador: 1,
          enviadas: 1,
          parciales: 0,
          recibidas: 0,
          canceladas: 0,
          monto_pendiente: 25000,
          pendientes_recepcion: 1,
        }),
      ),
      http.get('*/documentos-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_documentos: 2,
          monto_total: 35000,
          monto_confirmado: 25000,
          borradores: 1,
          confirmados: 1,
          anulados: 0,
          guias: 1,
          facturas: 1,
          boletas: 0,
          sin_recepcion: 1,
        }),
      ),
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-1', proveedor: 'p-1', numero: 'OC-001', estado: 'BORRADOR', fecha_emision: '2026-03-10', total: 10000 },
          { id: 'oc-2', proveedor: 'p-2', numero: 'OC-002', estado: 'ENVIADA', fecha_emision: '2026-03-10', total: 25000 },
        ]),
      ),
      http.get('*/documentos-compra/', async () => HttpResponse.json([])),
      http.get('*/proveedores/', async () =>
        HttpResponse.json([
          { id: 'p-1', contacto: 'c-1' },
          { id: 'p-2', contacto: 'c-2' },
        ]),
      ),
      http.get('*/contactos/', async () =>
        HttpResponse.json([
          { id: 'c-1', nombre: 'Proveedor Norte' },
          { id: 'c-2', nombre: 'Proveedor Sur' },
        ]),
      ),
    )

    renderWithProviders(<ComprasOrdenesListPage />, {
      preloadedState: authState(['COMPRAS.VER', 'COMPRAS.CREAR', 'COMPRAS.EDITAR', 'COMPRAS.APROBAR', 'COMPRAS.ANULAR', 'COMPRAS.BORRAR']),
    })

    expect(await screen.findByText('OC-001')).toBeInTheDocument()
    expect(screen.getByText('OC-002')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver reportes' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver resumen' })).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('Buscar por numero, proveedor o estado...'), 'Sur')

    expect(screen.queryByText('OC-001')).not.toBeInTheDocument()
    expect(screen.getByText('OC-002')).toBeInTheDocument()
  })

  it('anula orden y muestra feedback', async () => {
    server.use(
      http.get('*/ordenes-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_ordenes: 1,
          monto_total: 10000,
          borrador: 1,
          enviadas: 0,
          parciales: 0,
          recibidas: 0,
          canceladas: 0,
          monto_pendiente: 0,
          pendientes_recepcion: 0,
        }),
      ),
      http.get('*/documentos-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_documentos: 0,
          monto_total: 0,
          monto_confirmado: 0,
          borradores: 0,
          confirmados: 0,
          anulados: 0,
          guias: 0,
          facturas: 0,
          boletas: 0,
          sin_recepcion: 0,
        }),
      ),
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-1', proveedor: 'p-1', numero: 'OC-001', estado: 'BORRADOR', fecha_emision: '2026-03-10', total: 10000 },
        ]),
      ),
      http.get('*/documentos-compra/', async () => HttpResponse.json([])),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
      http.post('*/ordenes-compra/oc-1/anular/', async () => HttpResponse.json({ id: 'oc-1', estado: 'CANCELADA' })),
    )

    renderWithProviders(<ComprasOrdenesListPage />, {
      preloadedState: authState(['COMPRAS.VER', 'COMPRAS.ANULAR']),
    })

    await userEvent.click(await screen.findByRole('button', { name: 'Anular' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Orden anulada correctamente.')
    })
  })

  it('oculta acciones segun permiso y estado operativo', async () => {
    server.use(
      http.get('*/ordenes-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_ordenes: 1,
          monto_total: 25000,
          borrador: 0,
          enviadas: 1,
          parciales: 0,
          recibidas: 0,
          canceladas: 0,
          monto_pendiente: 25000,
          pendientes_recepcion: 1,
        }),
      ),
      http.get('*/documentos-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_documentos: 1,
          monto_total: 25000,
          monto_confirmado: 25000,
          borradores: 0,
          confirmados: 1,
          anulados: 0,
          guias: 1,
          facturas: 0,
          boletas: 0,
          sin_recepcion: 1,
        }),
      ),
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-2', proveedor: 'p-1', numero: 'OC-002', estado: 'ENVIADA', fecha_emision: '2026-03-10', total: 25000, tiene_documentos: false, tiene_documentos_activos: false },
        ]),
      ),
      http.get('*/documentos-compra/', async () => HttpResponse.json([])),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
    )

    renderWithProviders(<ComprasOrdenesListPage />, {
      preloadedState: authState(['COMPRAS.VER']),
    })

    expect(await screen.findByText('OC-002')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nueva orden' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enviar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Anular' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Duplicar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Crear doc' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Recepcion' })).not.toBeInTheDocument()
  })

  it('muestra resumen ejecutivo del abastecimiento', async () => {
    server.use(
      http.get('*/ordenes-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_ordenes: 4,
          monto_total: 600000,
          borrador: 1,
          enviadas: 2,
          parciales: 1,
          recibidas: 0,
          canceladas: 0,
          monto_pendiente: 450000,
          pendientes_recepcion: 3,
        }),
      ),
      http.get('*/documentos-compra/resumen_operativo/', async () =>
        HttpResponse.json({
          total_documentos: 5,
          monto_total: 450000,
          monto_confirmado: 320000,
          borradores: 1,
          confirmados: 3,
          anulados: 1,
          guias: 2,
          facturas: 2,
          boletas: 1,
          sin_recepcion: 2,
        }),
      ),
    )

    renderWithProviders(<ComprasResumenPage />, {
      preloadedState: authState(['COMPRAS.VER']),
    })

    expect(await screen.findByText('Monto comprometido')).toBeInTheDocument()
    expect(screen.getByText(/\$?\s*600\.000/)).toBeInTheDocument()
    expect(screen.getByText('Pendientes de recepcion: 3')).toBeInTheDocument()
    expect(screen.getByText('Documentos de compra')).toBeInTheDocument()
    expect(screen.getByText('Pendientes documentales')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a reportes' })).toBeInTheDocument()
  })

  it('muestra reportes exportables de compras', async () => {
    const ordenesAnalyticsBase = {
      filters: { agrupacion: 'mensual' },
      metrics: {
        total_ordenes: 2,
        monto_comprometido: 600000,
        pendientes_recepcion: 1,
        enviadas: 1,
        parciales: 0,
        recibidas: 1,
      },
      top_proveedores: [
        { proveedor_id: 'p-2', nombre: 'Proveedor Sur', total: 500000 },
        { proveedor_id: 'p-1', nombre: 'Proveedor Norte', total: 100000 },
      ],
      top_productos: [
        { producto_id: 'prod-2', nombre: 'Vacuna felina', cantidad: 5, monto: 100000 },
      ],
      series: [{ periodo: '2026-03-01', cantidad: 2, monto: 600000 }],
      detail: [
        { id: 'oc-1', numero: 'OC-001', fecha_emision: '2026-03-10', estado: 'ENVIADA', total: 100000, proveedor_id: 'p-1', proveedor_nombre: 'Proveedor Norte' },
        { id: 'oc-2', numero: 'OC-002', fecha_emision: '2026-03-18', estado: 'RECIBIDA', total: 500000, proveedor_id: 'p-2', proveedor_nombre: 'Proveedor Sur' },
      ],
    }
    const ordenesAnalyticsFiltrado = {
      filters: { agrupacion: 'semanal' },
      metrics: {
        total_ordenes: 1,
        monto_comprometido: 500000,
        pendientes_recepcion: 0,
        enviadas: 0,
        parciales: 0,
        recibidas: 1,
      },
      top_proveedores: [{ proveedor_id: 'p-2', nombre: 'Proveedor Sur', total: 500000 }],
      top_productos: [
        { producto_id: 'prod-2', nombre: 'Vacuna felina', cantidad: 5, monto: 100000 },
      ],
      series: [{ periodo: '2026-W12', cantidad: 1, monto: 500000 }],
      detail: [
        { id: 'oc-2', numero: 'OC-002', fecha_emision: '2026-03-18', estado: 'RECIBIDA', total: 500000, proveedor_id: 'p-2', proveedor_nombre: 'Proveedor Sur' },
      ],
    }
    const documentosAnalyticsBase = {
      filters: { agrupacion: 'mensual' },
      metrics: {
        total_documentos: 2,
        monto_documental: 200000,
        monto_confirmado: 120000,
        pendientes_documentales: 1,
        facturas: 1,
        guias: 1,
        boletas: 0,
      },
      top_proveedores: [{ proveedor_id: 'p-1', nombre: 'Proveedor Norte', total: 120000 }],
      top_productos: [{ producto_id: 'prod-1', nombre: 'Alimento premium', cantidad: 3, monto: 30000 }],
      series: [{ periodo: '2026-03-01', cantidad: 2, monto: 200000 }],
      detail: [
        { id: 'dc-1', tipo_documento: 'FACTURA_COMPRA', folio: '123', fecha_emision: '2026-03-10', estado: 'CONFIRMADO', total: 120000, proveedor_id: 'p-1', proveedor_nombre: 'Proveedor Norte' },
      ],
    }
    const documentosAnalyticsFiltrado = {
      ...documentosAnalyticsBase,
      filters: { agrupacion: 'semanal' },
      series: [{ periodo: '2026-W12', cantidad: 1, monto: 120000 }],
    }

    server.use(
      http.get('*/ordenes-compra/analytics/', async ({ request }) => {
        const url = new URL(request.url)
        const estado = url.searchParams.get('estado')
        const agrupacion = url.searchParams.get('agrupacion')
        if (estado === 'RECIBIDA' && agrupacion === 'semanal') {
          return HttpResponse.json(ordenesAnalyticsFiltrado)
        }
        return HttpResponse.json(ordenesAnalyticsBase)
      }),
      http.get('*/documentos-compra/analytics/', async ({ request }) => {
        const url = new URL(request.url)
        const agrupacion = url.searchParams.get('agrupacion')
        if (agrupacion === 'semanal') {
          return HttpResponse.json(documentosAnalyticsFiltrado)
        }
        return HttpResponse.json(documentosAnalyticsBase)
      }),
      http.get('*/proveedores/', async () =>
        HttpResponse.json([
          { id: 'p-1', contacto: 'c-1' },
          { id: 'p-2', contacto: 'c-2' },
        ]),
      ),
      http.get('*/contactos/', async () =>
        HttpResponse.json([
          { id: 'c-1', nombre: 'Proveedor Norte' },
          { id: 'c-2', nombre: 'Proveedor Sur' },
        ]),
      ),
    )

    renderWithProviders(<ComprasReportesPage />, {
      preloadedState: authState(['COMPRAS.VER']),
    })

    expect(await screen.findByText('Reporte operativo')).toBeInTheDocument()
    expect(screen.getByLabelText('Proveedor')).toBeInTheDocument()
    expect(screen.getByText('Monto comprometido')).toBeInTheDocument()
    expect(screen.getByText('Top proveedores por monto')).toBeInTheDocument()
    expect(screen.getByText('Top productos comprados')).toBeInTheDocument()
    expect(screen.getByText('Tendencia mensual de ordenes')).toBeInTheDocument()
    expect(screen.getByText('Reporte documental')).toBeInTheDocument()
    expect(screen.getAllByText('Proveedor Norte').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Proveedor Sur').length).toBeGreaterThan(0)

    await userEvent.selectOptions(screen.getByLabelText('Estado de orden'), 'RECIBIDA')
    await userEvent.selectOptions(screen.getByLabelText('Agrupacion temporal'), 'semanal')

    await waitFor(() => {
      expect(screen.getByText('Tendencia semanal de ordenes')).toBeInTheDocument()
    })
    expect(screen.queryByText('OC-001')).not.toBeInTheDocument()
    expect(screen.getAllByText('Proveedor Sur').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/\$?\s*500\.000/).length).toBeGreaterThan(0)
  })
})
