import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ContabilidadAsientosPage from '@/modules/contabilidad/pages/ContabilidadAsientosPage'
import ContabilidadPlanPage from '@/modules/contabilidad/pages/ContabilidadPlanPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

function authState(permissions = ['CONTABILIDAD.VER']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'contabilidad@eldanor.cl',
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

describe('contabilidad/pages integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('permite inicializar plan base y refresca el listado', async () => {
    let cuentas = [
      {
        id: 'cta-1',
        codigo: '110100',
        nombre: 'Caja',
        tipo: 'ACTIVO',
        padre: null,
        acepta_movimientos: true,
        activa: true,
      },
    ]

    server.use(
      http.get('*/plan-cuentas/', async () => HttpResponse.json(cuentas)),
      http.post('*/plan-cuentas/seed_base/', async () => {
        cuentas = [
          ...cuentas,
          {
            id: 'cta-2',
            codigo: '111200',
            nombre: 'Banco estado',
            tipo: 'ACTIVO',
            padre: null,
            acepta_movimientos: true,
            activa: true,
          },
        ]
        return HttpResponse.json({ created: 1 })
      }),
    )

    renderWithProviders(<ContabilidadPlanPage />, {
      preloadedState: authState(['CONTABILIDAD.VER', 'CONTABILIDAD.CONTABILIZAR']),
    })

    expect(await screen.findByRole('heading', { name: 'Plan de cuentas' })).toBeInTheDocument()
    expect(await screen.findByText('110100')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Inicializar plan base' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Plan base sincronizado. 1 cuentas nuevas.')
    })

    expect(await screen.findByText('111200')).toBeInTheDocument()
    expect(screen.getByText('Banco estado')).toBeInTheDocument()
  })

  it('permite procesar solicitudes y contabilizar un borrador', async () => {
    let procesadas = 0
    let contabilizadas = 0
    let asientos = [
      {
        id: 'asi-1',
        numero: 'ASI-001',
        fecha: '2026-03-19',
        glosa: 'Factura FV-001',
        origen: 'INTEGRACION',
        total_debe: 1190,
        total_haber: 1190,
        estado: 'BORRADOR',
      },
    ]

    server.use(
      http.get('*/plan-cuentas/', async () =>
        HttpResponse.json([
          {
            id: 'cta-1',
            codigo: '112100',
            nombre: 'Clientes nacionales',
            activa: true,
            acepta_movimientos: true,
          },
        ]),
      ),
      http.get('*/asientos-contables/', async () => HttpResponse.json(asientos)),
      http.post('*/asientos-contables/procesar_solicitudes/', async () => {
        procesadas += 1
        return HttpResponse.json({ processed: 1 })
      }),
      http.post('*/asientos-contables/asi-1/contabilizar/', async () => {
        contabilizadas += 1
        asientos = asientos.map((item) => (
          item.id === 'asi-1'
            ? { ...item, estado: 'CONTABILIZADO' }
            : item
        ))
        return HttpResponse.json({ id: 'asi-1', estado: 'CONTABILIZADO' })
      }),
    )

    renderWithProviders(<ContabilidadAsientosPage />, {
      preloadedState: authState(['CONTABILIDAD.VER', 'CONTABILIDAD.CONTABILIZAR']),
    })

    expect(await screen.findByRole('heading', { name: 'Asientos contables' })).toBeInTheDocument()
    expect(await screen.findByText('ASI-001')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Procesar solicitudes' }))

    await waitFor(() => {
      expect(procesadas).toBe(1)
      expect(toast.success).toHaveBeenCalledWith('Solicitudes procesadas: 1.')
    })

    await userEvent.click(screen.getByRole('button', { name: 'Contabilizar' }))

    await waitFor(() => {
      expect(contabilizadas).toBe(1)
      expect(toast.success).toHaveBeenCalledWith('Asiento contabilizado.')
    })

    expect(await screen.findByText('CONTABILIZADO')).toBeInTheDocument()
    expect(screen.getByText('Listo')).toBeInTheDocument()
  })
})