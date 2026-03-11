import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ComprasOrdenesListPage from '@/modules/compras/pages/ComprasOrdenesListPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

describe('compras/ListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lista registros y permite filtrar/buscar', async () => {
    server.use(
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-1', proveedor: 'p-1', numero: 'OC-001', estado: 'BORRADOR', fecha_emision: '2026-03-10', total: 10000 },
          { id: 'oc-2', proveedor: 'p-2', numero: 'OC-002', estado: 'ENVIADA', fecha_emision: '2026-03-10', total: 25000 },
        ]),
      ),
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

    renderWithProviders(<ComprasOrdenesListPage />)

    expect(await screen.findByText('OC-001')).toBeInTheDocument()
    expect(screen.getByText('OC-002')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('Buscar por numero, proveedor o estado...'), 'Sur')

    expect(screen.queryByText('OC-001')).not.toBeInTheDocument()
    expect(screen.getByText('OC-002')).toBeInTheDocument()
  })

  it('anula orden y muestra feedback', async () => {
    server.use(
      http.get('*/ordenes-compra/', async () =>
        HttpResponse.json([
          { id: 'oc-1', proveedor: 'p-1', numero: 'OC-001', estado: 'BORRADOR', fecha_emision: '2026-03-10', total: 10000 },
        ]),
      ),
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Norte' }])),
      http.post('*/ordenes-compra/oc-1/anular/', async () => HttpResponse.json({ id: 'oc-1', estado: 'CANCELADA' })),
    )

    renderWithProviders(<ComprasOrdenesListPage />)

    await userEvent.click(await screen.findByRole('button', { name: 'Anular' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Orden anulada correctamente.')
    })
  })
})
