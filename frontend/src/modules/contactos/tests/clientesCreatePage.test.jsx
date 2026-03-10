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

  it('crea contacto+cliente cuando no existe contacto previo (contrato frontend-backend)', async () => {
    let contactoPayload = null
    let clientePayload = null

    server.use(
      http.get('*/contactos/', async () => HttpResponse.json([])),
      http.post('*/contactos/', async ({ request }) => {
        contactoPayload = await request.json()
        return HttpResponse.json({ id: 301, ...contactoPayload }, { status: 201 })
      }),
      http.post('*/clientes/', async ({ request }) => {
        clientePayload = await request.json()
        return HttpResponse.json({ id: 401, ...clientePayload }, { status: 201 })
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

    expect(contactoPayload).toMatchObject({
      nombre: 'Cliente Nuevo',
      rut: '12.345.678-5',
      email: 'cliente@eldanor.cl',
    })
    expect(clientePayload).toMatchObject({
      contacto: 301,
      limite_credito: 90000,
      dias_credito: 30,
    })
  })

  it('reutiliza contacto existente por RUT y evita crear contacto duplicado', async () => {
    let contactoPostCalled = false
    let clientePayload = null

    server.use(
      http.get('*/contactos/', async () =>
        HttpResponse.json([
          {
            id: 77,
            nombre: 'Cliente Existente',
            rut: '123456785',
            email: 'existente@eldanor.cl',
          },
        ]),
      ),
      http.post('*/contactos/', async () => {
        contactoPostCalled = true
        return HttpResponse.json({ id: 999 }, { status: 201 })
      }),
      http.post('*/clientes/', async ({ request }) => {
        clientePayload = await request.json()
        return HttpResponse.json({ id: 1001 }, { status: 201 })
      }),
    )

    renderWithProviders(<ClientesCreatePage />)

    await userEvent.type(screen.getByLabelText('Nombre'), 'Cliente Existente')
    await userEvent.type(screen.getByLabelText('RUT'), '12.345.678-5')
    await userEvent.type(screen.getByLabelText('Email'), 'existente@eldanor.cl')

    await userEvent.click(screen.getByRole('button', { name: 'Crear cliente' }))

    await waitFor(() => {
      expect(toast.info).toHaveBeenCalledWith('Se reutilizo un contacto existente para crear el cliente.')
      expect(toast.success).toHaveBeenCalledWith('Cliente creado correctamente.')
    })

    expect(contactoPostCalled).toBe(false)
    expect(clientePayload?.contacto).toBe(77)
  })
})
