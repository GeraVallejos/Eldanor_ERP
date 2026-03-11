import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PresupuestosCreatePage from '@/modules/presupuestos/pages/PresupuestosCreatePage'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

describe('presupuestos/PresupuestosCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    invalidateProductosCatalogCache()
  })

  it('muestra errores inline de item cuando se envia sin producto', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 1, contacto: 10 }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 10, nombre: 'Cliente A' }])),
      http.get('*/productos/', async () => HttpResponse.json([])),
      http.get('*/impuestos/', async () => HttpResponse.json([])),
    )

    renderWithProviders(<PresupuestosCreatePage />)

    await userEvent.click(await screen.findByRole('button', { name: 'Crear presupuesto' }))

    expect(await screen.findByText('Debes seleccionar un producto.')).toBeInTheDocument()
    expect(await screen.findByText('La descripcion es obligatoria.')).toBeInTheDocument()
  })

  it('crea presupuesto e item con seleccion de cliente/producto desde buscadores', async () => {
    let presupuestoPayload = null
    let itemPayload = null

    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 501, contacto: 601 }])),
      http.get('*/contactos/', async () =>
        HttpResponse.json([{ id: 601, nombre: 'Cliente Demo', rut: '11.111.111-1' }]),
      ),
      http.get('*/productos/', async () =>
        HttpResponse.json([
          {
            id: 700,
            nombre: 'Producto A',
            tipo: 'PRODUCTO',
            precio_referencia: 35000,
            impuesto: 5,
          },
        ]),
      ),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 5, nombre: 'IVA', porcentaje: 19 }])),
      http.post('*/presupuestos/', async ({ request }) => {
        presupuestoPayload = await request.json()
        return HttpResponse.json({ id: 900, ...presupuestoPayload }, { status: 201 })
      }),
      http.post('*/presupuesto-items/', async ({ request }) => {
        itemPayload = await request.json()
        return HttpResponse.json({ id: 901, ...itemPayload }, { status: 201 })
      }),
    )

    renderWithProviders(<PresupuestosCreatePage />)

    const clienteInput = await screen.findByPlaceholderText('Buscar y seleccionar cliente...')
    await userEvent.type(clienteInput, 'Cliente Demo')

    const productoInput = screen.getByPlaceholderText('Buscar producto...')
    await userEvent.type(productoInput, 'Producto A')
    await userEvent.clear(screen.getByLabelText('Descripcion'))
    await userEvent.type(screen.getByLabelText('Descripcion'), 'Producto A')
    await userEvent.clear(screen.getByLabelText('Precio unitario'))
    await userEvent.type(screen.getByLabelText('Precio unitario'), '35000')
    await userEvent.selectOptions(screen.getByLabelText('Impuesto'), '5')

    await userEvent.click(screen.getByRole('button', { name: 'Crear presupuesto' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Presupuesto creado correctamente.')
    })

    expect(presupuestoPayload).toMatchObject({
      cliente: '501',
    })
    expect(itemPayload).toMatchObject({
      presupuesto: 900,
      producto: '700',
      descripcion: 'Producto A',
      cantidad: 1,
      precio_unitario: 35000,
      impuesto: '5',
    })
  })
})
