import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProductosCreatePage from '@/modules/productos/pages/ProductosCreatePage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

describe('productos/ProductosCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra contrato de error backend al crear producto', async () => {
    server.use(
      http.get('*/categorias/', async () => HttpResponse.json([{ id: 1, nombre: 'General' }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.post('*/productos/', async () =>
        HttpResponse.json(
          {
            detail: { sku: ['Ya existe un producto con este SKU.'] },
            error_code: 'CONFLICT',
          },
          { status: 409 },
        ),
      ),
    )

    renderWithProviders(<ProductosCreatePage />, {
      preloadedState: {
        auth: {
          user: {
            id: 10,
            email: 'catalogo@erp.test',
            permissions: ['PRODUCTOS.CREAR'],
          },
          empresas: [],
          empresasStatus: 'idle',
          empresasError: null,
          changingEmpresaId: null,
          isAuthenticated: true,
          status: 'succeeded',
          bootstrapStatus: 'succeeded',
          error: null,
        },
      },
    })

    await userEvent.type(await screen.findByLabelText('Nombre'), 'Vacuna antirrabica')
    await userEvent.type(screen.getByLabelText('SKU'), 'VAC-001')
    await userEvent.clear(screen.getByLabelText('Precio referencia'))
    await userEvent.type(screen.getByLabelText('Precio referencia'), '12000')
    await userEvent.clear(screen.getByLabelText('Precio costo'))
    await userEvent.type(screen.getByLabelText('Precio costo'), '7000')
    await userEvent.click(screen.getByRole('button', { name: 'Crear producto' }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled()
    })

    expect(await screen.findByText(/Ya existe un producto con este SKU/i)).toBeInTheDocument()
    expect(screen.getByText(/Codigo: CONFLICT/i)).toBeInTheDocument()
  })

  it('bloquea la creacion cuando el usuario no tiene permiso', async () => {
    server.use(
      http.get('*/categorias/', async () => HttpResponse.json([{ id: 1, nombre: 'General' }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
    )

    renderWithProviders(<ProductosCreatePage />, {
      preloadedState: {
        auth: {
          user: {
            id: 11,
            email: 'viewer@erp.test',
            permissions: ['PRODUCTOS.VER'],
          },
          empresas: [],
          empresasStatus: 'idle',
          empresasError: null,
          changingEmpresaId: null,
          isAuthenticated: true,
          status: 'succeeded',
          bootstrapStatus: 'succeeded',
          error: null,
        },
      },
    })

    await userEvent.type(await screen.findByLabelText('Nombre'), 'Vacuna triple')
    await userEvent.type(screen.getByLabelText('SKU'), 'VAC-002')
    await userEvent.clear(screen.getByLabelText('Precio referencia'))
    await userEvent.type(screen.getByLabelText('Precio referencia'), '15000')
    await userEvent.clear(screen.getByLabelText('Precio costo'))
    await userEvent.type(screen.getByLabelText('Precio costo'), '9000')
    await userEvent.click(screen.getByRole('button', { name: 'Crear producto' }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No tiene permiso para crear productos.')
    })
  })
})
