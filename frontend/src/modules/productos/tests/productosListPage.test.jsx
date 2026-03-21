import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ProductosListPage from '@/modules/productos/pages/ProductosListPage'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('productos/ProductosListPage', () => {
  it('oculta acciones de escritura cuando el usuario solo tiene permiso de lectura', async () => {
    renderWithProviders(<ProductosListPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 10,
            email: 'lector@erp.test',
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

    expect(await screen.findByText('Servicio de poda')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nuevo producto' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument()
  })

  it('no muestra carga masiva si el usuario no cumple la regla de rol admin', async () => {
    renderWithProviders(<ProductosListPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 11,
            email: 'owner@erp.test',
            rol: 'OWNER',
            permissions: ['PRODUCTOS.VER', 'PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'],
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

    expect(await screen.findByText('Servicio de poda')).toBeInTheDocument()
    expect(screen.queryByText(/Carga masiva/i)).not.toBeInTheDocument()
  })
})
