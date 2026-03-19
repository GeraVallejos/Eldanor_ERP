import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VentasPedidosListPage from '@/modules/ventas/pages/VentasPedidosListPage'
import VentasFacturasListPage from '@/modules/ventas/pages/VentasFacturasListPage'
import VentasNotasListPage from '@/modules/ventas/pages/VentasNotasListPage'
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
    await userEvent.click(screen.getByRole('button', { name: 'Emitir' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Factura actualizada.')
    })
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
})
