import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ComprasOrdenesCreatePage from '@/modules/compras/pages/ComprasOrdenesCreatePage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  }
})

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

describe('compras/CreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('crea registro y muestra feedback al usuario', async () => {
    let ordenPayload = null
    let itemPayload = null

    server.use(
      http.get('*/proveedores/', async () => HttpResponse.json([{ id: 'p-1', contacto: 'c-1' }])),
      http.get('*/contactos/', async () => HttpResponse.json([{ id: 'c-1', nombre: 'Proveedor Uno' }])),
      http.get('*/productos/', async () =>
        HttpResponse.json([{ id: 'prod-1', nombre: 'Producto A', tipo: 'PRODUCTO', precio_referencia: 1000, impuesto: 'imp-1' }]),
      ),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 'imp-1', nombre: 'IVA', porcentaje: 19 }])),
      http.post('*/ordenes-compra/', async ({ request }) => {
        ordenPayload = await request.json()
        return HttpResponse.json({ id: 'oc-200', ...ordenPayload }, { status: 201 })
      }),
      http.post('*/ordenes-compra-items/', async ({ request }) => {
        itemPayload = await request.json()
        return HttpResponse.json({ id: 'oci-1', ...itemPayload }, { status: 201 })
      }),
    )

    renderWithProviders(<ComprasOrdenesCreatePage />)

    await userEvent.selectOptions(await screen.findByLabelText('Proveedor'), 'p-1')
    await userEvent.type(screen.getByLabelText('Numero'), 'OC-200')
    await userEvent.selectOptions(screen.getAllByLabelText('Producto')[0], 'prod-1')

    await userEvent.click(screen.getByRole('button', { name: 'Crear orden' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Orden de compra creada correctamente.')
    })

    expect(ordenPayload).toMatchObject({
      proveedor: 'p-1',
      numero: 'OC-200',
      estado: 'BORRADOR',
    })

    expect(itemPayload).toMatchObject({
      orden_compra: 'oc-200',
      producto: 'prod-1',
      descripcion: 'Producto A',
    })
  })

  it('muestra errores inline de validacion', async () => {
    const createOrdenSpy = vi.fn()
    server.use(
      http.get('*/proveedores/', async () => HttpResponse.json([])),
      http.get('*/contactos/', async () => HttpResponse.json([])),
      http.get('*/productos/', async () => HttpResponse.json([])),
      http.get('*/impuestos/', async () => HttpResponse.json([])),
      http.post('*/ordenes-compra/', async ({ request }) => {
        createOrdenSpy(await request.json())
        return HttpResponse.json({ id: 'oc-err' }, { status: 201 })
      }),
    )

    renderWithProviders(<ComprasOrdenesCreatePage />)

    await userEvent.click(await screen.findByRole('button', { name: 'Crear orden' }))

    await waitFor(() => {
      expect(createOrdenSpy).not.toHaveBeenCalled()
    })
  })
})
