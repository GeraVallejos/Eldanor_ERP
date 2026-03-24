import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ClientesCreatePage from '@/modules/contactos/pages/ClientesCreatePage'
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

describe('contactos/ClientesCreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('crea contacto+cliente confiando en la deduplicacion backend', async () => {
    let requestPayload = null

    server.use(
      http.post('*/clientes/crear-con-contacto/', async ({ request }) => {
        requestPayload = await request.json()
        return HttpResponse.json({ id: 401, contacto: 301 }, { status: 201 })
      }),
    )

    renderWithProviders(<ClientesCreatePage />)

    await userEvent.type(screen.getByLabelText('Nombre'), 'Cliente Nuevo')
    await userEvent.type(screen.getByLabelText('RUT'), '12.345.678-5')
    await userEvent.type(screen.getByLabelText('Email'), 'cliente@eldanor.cl')
    await userEvent.type(screen.getByLabelText('Limite de credito'), '90000')
    await userEvent.type(screen.getByLabelText('Dias de credito'), '30')

    await userEvent.click(screen.getByRole('button', { name: 'Crear cliente' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Cliente creado correctamente.')
    })

    expect(requestPayload).toMatchObject({
      nombre: 'Cliente Nuevo',
      rut: '12.345.678-5',
      email: 'cliente@eldanor.cl',
      limite_credito: 90000,
      dias_credito: 30,
    })
    expect(requestPayload).toHaveProperty('activo', true)
  })

  it('usa el contacto devuelto por backend aunque el RUT ya exista y haya sido reutilizado', async () => {
    let requestPayload = null

    server.use(
      http.post('*/clientes/crear-con-contacto/', async ({ request }) => {
        requestPayload = await request.json()
        return HttpResponse.json(
          {
            id: 77,
            contacto: 77,
          },
          { status: 201 },
        )
      }),
    )

    renderWithProviders(<ClientesCreatePage />)

    await userEvent.type(screen.getByLabelText('Nombre'), 'Cliente Existente')
    await userEvent.type(screen.getByLabelText('RUT'), '12.345.678-5')
    await userEvent.type(screen.getByLabelText('Email'), 'existente@eldanor.cl')

    await userEvent.click(screen.getByRole('button', { name: 'Crear cliente' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Cliente creado correctamente.')
    })

    expect(requestPayload).toMatchObject({
      nombre: 'Cliente Existente',
      rut: '12.345.678-5',
      email: 'existente@eldanor.cl',
      activo: true,
    })
    expect(requestPayload).toMatchObject({
      categoria_cliente: null,
      segmento: null,
    })
  })
})
