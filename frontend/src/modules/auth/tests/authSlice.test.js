import { describe, expect, it } from 'vitest'
import { http, HttpResponse } from 'msw'
import { login, logout, selectIsAuthenticated } from '@/modules/auth/authSlice'
import { server } from '@/test/msw/server'
import { createTestStore } from '@/test/utils/createTestStore'

describe('authSlice', () => {
  it('hace login exitoso y marca sesion autenticada', async () => {
    const store = createTestStore()

    const result = await store.dispatch(
      login({
        email: 'admin@eldanor.cl',
        password: 'secret',
      }),
    )

    expect(result.type).toBe('auth/login/fulfilled')
    expect(selectIsAuthenticated(store.getState())).toBe(true)
    expect(store.getState().auth.user?.email).toBe('admin@eldanor.cl')
  })

  it('mapea mensaje de credenciales invalidas al contrato UX', async () => {
    server.use(
      http.post('*/token/', async () => {
        return HttpResponse.json(
          {
            detail: 'No active account found with the given credentials',
          },
          { status: 401 },
        )
      }),
    )

    const store = createTestStore()
    const result = await store.dispatch(
      login({
        email: 'mal@correo.cl',
        password: 'bad-password',
      }),
    )

    expect(result.type).toBe('auth/login/rejected')
    expect(result.payload).toBe('Correo o contrasena incorrectos.')
    expect(selectIsAuthenticated(store.getState())).toBe(false)
  })

  it('al hacer logout limpia estado compartido de auth', () => {
    const store = createTestStore({
      auth: {
        user: { id: 1, email: 'admin@eldanor.cl' },
        empresas: [{ id: 10, nombre: 'Empresa 1' }],
        empresasStatus: 'succeeded',
        empresasError: null,
        changingEmpresaId: null,
        isAuthenticated: true,
        status: 'succeeded',
        bootstrapStatus: 'succeeded',
        error: null,
      },
      productos: {
        items: [],
        status: 'idle',
        error: null,
        createStatus: 'idle',
        createError: null,
        categorias: [],
        impuestos: [],
        catalogStatus: 'idle',
        catalogError: null,
      },
    })

    store.dispatch(logout())

    expect(selectIsAuthenticated(store.getState())).toBe(false)
    expect(store.getState().auth.user).toBeNull()
    expect(store.getState().auth.empresas).toEqual([])
  })
})
