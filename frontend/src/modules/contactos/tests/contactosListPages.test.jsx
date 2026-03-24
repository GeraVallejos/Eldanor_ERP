import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ClientesListPage from '@/modules/contactos/pages/ClientesListPage'
import ProveedoresListPage from '@/modules/contactos/pages/ProveedoresListPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

function buildAuthState() {
  return {
    auth: {
      user: {
        id: 10,
        email: 'admin@erp.test',
        rol: 'ADMIN',
        permissions: ['CONTACTOS.VER', 'CONTACTOS.CREAR', 'CONTACTOS.EDITAR', 'CONTACTOS.BORRAR'],
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
}

describe('contactos list pages', () => {
  it('renderiza clientes usando contacto_resumen sin depender de /contactos/', async () => {
    server.use(
      http.get('*/clientes/', async () =>
        HttpResponse.json([
          {
            id: 'cli-1',
            contacto: 'c-1',
            contacto_resumen: {
              id: 'c-1',
              nombre: 'Cliente Embebido',
              rut: '12.345.678-5',
              email: 'cliente@erp.cl',
              telefono: '22334455',
              celular: '',
              activo: true,
            },
            limite_credito: 120000,
            dias_credito: 30,
          },
        ]),
      ),
      http.get('*/contactos/', async () => HttpResponse.json([], { status: 500 })),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/clientes" element={<ClientesListPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/clientes'],
        preloadedState: buildAuthState(),
      },
    )

    expect(await screen.findByText('Cliente Embebido')).toBeInTheDocument()
    expect(screen.getByText('12.345.678-5')).toBeInTheDocument()
    expect(screen.getByText('cliente@erp.cl')).toBeInTheDocument()
  })

  it('renderiza proveedores usando contacto_resumen sin depender de /contactos/', async () => {
    server.use(
      http.get('*/proveedores/', async () =>
        HttpResponse.json([
          {
            id: 'prov-1',
            contacto: 'c-2',
            contacto_resumen: {
              id: 'c-2',
              nombre: 'Proveedor Embebido',
              rut: '98.765.432-1',
              email: 'proveedor@erp.cl',
              telefono: '',
              celular: '99998888',
              activo: true,
            },
            giro: 'Servicios',
            dias_credito: 15,
          },
        ]),
      ),
      http.get('*/contactos/', async () => HttpResponse.json([], { status: 500 })),
    )

    renderWithProviders(
      <Routes>
        <Route path="/contactos/proveedores" element={<ProveedoresListPage />} />
      </Routes>,
      {
        initialEntries: ['/contactos/proveedores'],
        preloadedState: buildAuthState(),
      },
    )

    expect(await screen.findByText('Proveedor Embebido')).toBeInTheDocument()
    expect(screen.getByText('98.765.432-1')).toBeInTheDocument()
    expect(screen.getByText('proveedor@erp.cl')).toBeInTheDocument()
  })
})
