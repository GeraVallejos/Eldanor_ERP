import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import ClientesEditPage from '@/modules/contactos/pages/ClientesEditPage'
import ProveedoresEditPage from '@/modules/contactos/pages/ProveedoresEditPage'
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

const AUTH_STATE = {
  auth: {
    user: {
      id: 10,
      email: 'admin@erp.test',
      permissions: ['CONTACTOS.VER', 'CONTACTOS.EDITAR'],
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
}

describe('contactos edit pages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('actualiza cliente desde pagina dedicada y mantiene limpio el payload comercial', async () => {
    let clientePayload = null

    server.use(
      http.get('*/clientes/cli-1/detalle-edicion/', async () =>
        HttpResponse.json({
          id: 'cli-1',
          contacto: {
            id: 'c-1',
            nombre: 'Cliente Editado',
            razon_social: 'Cliente Editado SpA',
            rut: '12.345.678-5',
            tipo: 'EMPRESA',
            email: 'cliente@erp.cl',
            telefono: '22223333',
            celular: '99998888',
            notas: 'Inicial',
            activo: true,
          },
          limite_credito: 90000,
          dias_credito: 30,
          categoria_cliente: 'ORO',
          segmento: 'RETAIL',
        }),
      ),
      http.patch('*/clientes/cli-1/actualizar-con-contacto/', async ({ request }) => {
        clientePayload = await request.json()
        return HttpResponse.json({ id: 'cli-1', ...clientePayload })
      }),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/clientes/:id/editar" element={<ClientesEditPage />} />
        <Route path="/contactos/terceros/:id" element={<div>Detalle tercero</div>} />
      </Routes>,
      {
        initialEntries: ['/contactos/clientes/cli-1/editar'],
        preloadedState: AUTH_STATE,
      },
    )

    expect(await screen.findByDisplayValue('Cliente Editado')).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText('Nombre'))
    await userEvent.type(screen.getByLabelText('Nombre'), 'Cliente Enterprise')
    await userEvent.clear(screen.getByLabelText('Limite de credito'))
    await userEvent.type(screen.getByLabelText('Limite de credito'), '150000')
    await userEvent.clear(screen.getByLabelText('Segmento'))
    await userEvent.type(screen.getByLabelText('Segmento'), 'CORPORATIVO')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Cliente actualizado correctamente.')
    })

    expect(clientePayload).toMatchObject({
      nombre: 'Cliente Enterprise',
      rut: '12.345.678-5',
      email: 'cliente@erp.cl',
      activo: true,
      limite_credito: 150000,
      dias_credito: 30,
      segmento: 'CORPORATIVO',
    })
  })

  it('actualiza proveedor desde pagina dedicada y persiste su ficha operativa', async () => {
    let proveedorPayload = null

    server.use(
      http.get('*/proveedores/prov-1/detalle-edicion/', async () =>
        HttpResponse.json({
          id: 'prov-1',
          contacto: {
            id: 'c-9',
            nombre: 'Proveedor Base',
            razon_social: 'Proveedor Base Ltda.',
            rut: '98.765.432-1',
            tipo: 'EMPRESA',
            email: 'proveedor@erp.cl',
            telefono: '',
            celular: '',
            notas: '',
            activo: true,
          },
          giro: 'Servicios',
          vendedor_contacto: 'Ana Perez',
          dias_credito: 15,
        }),
      ),
      http.patch('*/proveedores/prov-1/actualizar-con-contacto/', async ({ request }) => {
        proveedorPayload = await request.json()
        return HttpResponse.json({ id: 'prov-1', ...proveedorPayload })
      }),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/proveedores/:id/editar" element={<ProveedoresEditPage />} />
        <Route path="/contactos/terceros/:id" element={<div>Detalle tercero</div>} />
      </Routes>,
      {
        initialEntries: ['/contactos/proveedores/prov-1/editar'],
        preloadedState: AUTH_STATE,
      },
    )

    expect(await screen.findByDisplayValue('Proveedor Base')).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText('Giro'))
    await userEvent.type(screen.getByLabelText('Giro'), 'Servicios industriales')
    await userEvent.clear(screen.getByLabelText('Contacto vendedor'))
    await userEvent.type(screen.getByLabelText('Contacto vendedor'), 'Beatriz Soto')
    await userEvent.clear(screen.getByLabelText('Dias de credito'))
    await userEvent.type(screen.getByLabelText('Dias de credito'), '45')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Proveedor actualizado correctamente.')
    })

    expect(proveedorPayload).toMatchObject({
      nombre: 'Proveedor Base',
      rut: '98.765.432-1',
      email: 'proveedor@erp.cl',
      activo: true,
      giro: 'Servicios industriales',
      vendedor_contacto: 'Beatriz Soto',
      dias_credito: 45,
    })
  })
})
