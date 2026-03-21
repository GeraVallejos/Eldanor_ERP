import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TesoreriaCuentasPage from '@/modules/tesoreria/pages/TesoreriaCuentasPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

function authState(permissions = ['TESORERIA.VER']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'tesoreria@eldanor.cl',
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

describe('tesoreria/TesoreriaCuentasPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('carga cartera y permite aplicar pago si tiene permiso', async () => {
    let cxc = [
      {
        id: 'cxc-1',
        referencia: 'FV-001',
        fecha_vencimiento: '2026-03-30',
        monto_total: 100000,
        saldo: 60000,
        estado: 'PARCIAL',
      },
    ]

    server.use(
      http.get('*/cuentas-por-cobrar/', async () => HttpResponse.json(cxc)),
      http.get('*/cuentas-por-pagar/', async () => HttpResponse.json([])),
      http.get('*/cuentas-por-cobrar/aging/', async () => HttpResponse.json({ totales: { al_dia: 0, '1_30': 60000, '31_60': 0, '61_90': 0, '91_plus': 0, total: 60000 } })),
      http.get('*/cuentas-por-pagar/aging/', async () => HttpResponse.json({ totales: { al_dia: 0, '1_30': 0, '31_60': 0, '61_90': 0, '91_plus': 0, total: 0 } })),
      http.post('*/cuentas-por-cobrar/cxc-1/aplicar_pago/', async () => {
        cxc = [
          {
            ...cxc[0],
            saldo: 30000,
            estado: 'PARCIAL',
          },
        ]
        return HttpResponse.json({ ...cxc[0] })
      }),
    )

    renderWithProviders(<TesoreriaCuentasPage />, {
      preloadedState: authState(['TESORERIA.VER', 'TESORERIA.COBRAR']),
    })

    expect(await screen.findByRole('heading', { name: 'Cartera' })).toBeInTheDocument()
    expect(await screen.findByText('FV-001')).toBeInTheDocument()
    expect(await screen.findByText('Antiguedad de saldos CxC')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Aplicar pago' }))
    const paymentForm = screen.getByRole('button', { name: 'Confirmar' }).closest('form')
    expect(paymentForm).not.toBeNull()
    const montoInput = within(paymentForm).getByRole('spinbutton', { name: /Monto/ })
    const fechaPagoInput = within(paymentForm).getByLabelText('Fecha pago')
    await userEvent.clear(montoInput)
    await userEvent.type(montoInput, '30000')
    await userEvent.type(fechaPagoInput, '2026-03-20')
    await userEvent.click(within(paymentForm).getByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Pago aplicado correctamente.')
    })

    expect(await screen.findByText((content) => content.includes('30.000'))).toBeInTheDocument()
  })

  it('muestra mensaje si no tiene permiso de visualizacion', async () => {
    renderWithProviders(<TesoreriaCuentasPage />, {
      preloadedState: authState([]),
    })

    expect(await screen.findByText(/No tiene permiso para ver tesorer/i)).toBeInTheDocument()
  })

  it('oculta aplicar pago cuando la cuenta ya no admite cobro por estado', async () => {
    server.use(
      http.get('*/cuentas-por-cobrar/', async () =>
        HttpResponse.json([
          {
            id: 'cxc-2',
            referencia: 'FV-002',
            fecha_vencimiento: '2026-03-30',
            monto_total: 100000,
            saldo: 0,
            estado: 'PAGADA',
          },
        ]),
      ),
      http.get('*/cuentas-por-pagar/', async () => HttpResponse.json([])),
      http.get('*/cuentas-por-cobrar/aging/', async () => HttpResponse.json({ totales: { al_dia: 0, '1_30': 0, '31_60': 0, '61_90': 0, '91_plus': 0, total: 0 } })),
      http.get('*/cuentas-por-pagar/aging/', async () => HttpResponse.json({ totales: { al_dia: 0, '1_30': 0, '31_60': 0, '61_90': 0, '91_plus': 0, total: 0 } })),
    )

    renderWithProviders(<TesoreriaCuentasPage />, {
      preloadedState: authState(['TESORERIA.VER', 'TESORERIA.COBRAR']),
    })

    expect(await screen.findByText('FV-002')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Aplicar pago' })).not.toBeInTheDocument()
    expect(screen.getByText('No aplica')).toBeInTheDocument()
  })
})
