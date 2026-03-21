import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Route, Routes } from 'react-router-dom'
import HomeRedirectPage from '@/modules/shared/pages/HomeRedirectPage'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

function authState(permissions = []) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'user@test.com',
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

describe('HomeRedirectPage', () => {
  it('muestra estado vacio cuando el usuario no tiene modulos visibles', async () => {
    renderWithProviders(<HomeRedirectPage />, {
      preloadedState: authState([]),
    })

    expect(await screen.findByText('Sin modulos disponibles')).toBeInTheDocument()
  })

  it('redirige a presupuestos cuando es la unica opcion visible dentro de ventas', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/" element={<HomeRedirectPage />} />
        <Route path="/presupuestos" element={<div>Presupuestos page</div>} />
      </Routes>,
      {
        preloadedState: authState(['PRESUPUESTOS.VER']),
        initialEntries: ['/'],
      },
    )

    expect(await screen.findByText('Presupuestos page')).toBeInTheDocument()
  })
})
