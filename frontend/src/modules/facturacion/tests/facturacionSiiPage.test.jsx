import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FacturacionSiiPage from '@/modules/facturacion/pages/FacturacionSiiPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

function authState(permissions = ['FACTURACION.VER']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'admin@eldanor.cl',
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

describe('facturacion/FacturacionSiiPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga configuracion y registra un rango tributario', async () => {
    let rangos = [
      {
        id: 'rng-1',
        tipo_documento: 'FACTURA_VENTA',
        caf_nombre: 'CAF 2026',
        folio_desde: 100,
        folio_hasta: 150,
        folio_actual: 140,
        fecha_vencimiento: '2026-12-31',
        activo: true,
      },
    ]

    server.use(
      http.get('*/configuracion-tributaria/', async () => HttpResponse.json([
        {
          id: 'cfg-1',
          ambiente: 'CERTIFICACION',
          rut_emisor: '76086428-5',
          razon_social: 'Clinica Veterinaria Eldanor',
          certificado_alias: 'eldanor-cert',
          certificado_activo: true,
          resolucion_numero: '80',
          resolucion_fecha: '2026-01-01',
          email_intercambio_dte: 'dte@eldanor.cl',
          proveedor_envio: 'INTERNO',
          activa: true,
        },
      ])),
      http.get('*/rangos-folios-tributarios/', async () => HttpResponse.json(rangos)),
      http.post('*/rangos-folios-tributarios/', async () => {
        rangos = [
          ...rangos,
          {
            id: 'rng-2',
            tipo_documento: 'GUIA_DESPACHO',
            caf_nombre: 'CAF GUIAS',
            folio_desde: 500,
            folio_hasta: 600,
            folio_actual: 500,
            fecha_vencimiento: '2026-12-31',
            activo: true,
          },
        ]
        return HttpResponse.json(rangos[1], { status: 201 })
      }),
    )

    renderWithProviders(<FacturacionSiiPage />, {
      preloadedState: authState(['FACTURACION.VER', 'FACTURACION.EDITAR']),
    })

    expect(await screen.findByRole('heading', { name: 'SII y DTE' })).toBeInTheDocument()
    expect(await screen.findByDisplayValue('Clinica Veterinaria Eldanor')).toBeInTheDocument()
    expect(await screen.findByText('CAF 2026')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Nombre CAF'), 'CAF GUIAS')
    await userEvent.clear(screen.getByLabelText('Folio desde'))
    await userEvent.type(screen.getByLabelText('Folio desde'), '500')
    await userEvent.clear(screen.getByLabelText('Folio hasta'))
    await userEvent.type(screen.getByLabelText('Folio hasta'), '600')
    await userEvent.type(screen.getByLabelText('Fecha autorizacion'), '2026-01-01')
    await userEvent.type(screen.getByLabelText('Fecha vencimiento'), '2026-12-31')
    await userEvent.selectOptions(screen.getByLabelText('Tipo documento'), 'GUIA_DESPACHO')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar rango' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Rango tributario registrado.')
    })

    expect(await screen.findByText('CAF GUIAS')).toBeInTheDocument()
    expect((await screen.findAllByText('Guia despacho')).length).toBeGreaterThan(0)
  })

  it('muestra mensaje de acceso denegado sin permiso de facturacion', async () => {
    renderWithProviders(<FacturacionSiiPage />, {
      preloadedState: authState([]),
    })

    expect(await screen.findByText(/No tiene permiso para revisar configuracion SII/i)).toBeInTheDocument()
  })
})
