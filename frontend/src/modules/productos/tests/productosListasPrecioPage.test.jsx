import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProductosListasPrecioPage from '@/modules/productos/pages/ProductosListasPrecioPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

describe('productos/ProductosListasPrecioPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra niveles comerciales legibles y habilita importacion sobre la lista seleccionada', async () => {
    server.use(
      http.get('*/listas-precio/', async () =>
        HttpResponse.json({
          results: [
            {
              id: 'lista-1',
              nombre: 'Mayorista Norte',
              moneda: 'mon-1',
              moneda_codigo: 'CLP',
              cliente: null,
              cliente_nombre: null,
              fecha_desde: '2026-01-01',
              fecha_hasta: null,
              activa: true,
              prioridad: 100,
              prioridad_label: 'Normal',
            },
          ],
        }),
      ),
      http.get('*/monedas/', async () =>
        HttpResponse.json({
          results: [
            { id: 'mon-1', codigo: 'CLP', nombre: 'Peso chileno' },
          ],
        }),
      ),
      http.get('*/clientes/', async () =>
        HttpResponse.json({
          results: [],
        }),
      ),
    )

    renderWithProviders(<ProductosListasPrecioPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 10,
            email: 'admin@erp.test',
            permissions: ['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR'],
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

    expect(await screen.findByText('Listas de precio')).toBeInTheDocument()
    expect(screen.getByLabelText('Nivel comercial')).toHaveDisplayValue('Normal')
    const priorityMatches = await screen.findAllByText((_, element) =>
      String(element?.textContent || '').includes('sin termino | Normal | Activa'),
    )
    expect(priorityMatches.length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Gestionar precios' })).toHaveAttribute('href', '/productos/listas-precio/lista-1')
  })

  it('bloquea el guardado de listas cuando el usuario no tiene permiso', async () => {
    const user = userEvent.setup()

    server.use(
      http.get('*/listas-precio/', async () => HttpResponse.json({ results: [] })),
      http.get('*/monedas/', async () =>
        HttpResponse.json({
          results: [{ id: 'mon-1', codigo: 'CLP', nombre: 'Peso chileno' }],
        }),
      ),
      http.get('*/clientes/', async () => HttpResponse.json({ results: [] })),
    )

    renderWithProviders(<ProductosListasPrecioPage />, {
      preloadedState: {
        auth: {
          user: {
            id: 12,
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

    await screen.findByText('Listas de precio')
    await user.type(screen.getByLabelText('Nombre lista'), 'Lista restringida')
    await user.selectOptions(screen.getByLabelText('Moneda'), 'mon-1')
    await user.type(screen.getByLabelText('Vigencia desde'), '2026-03-23')
    await user.click(screen.getByRole('button', { name: 'Crear lista' }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('No tiene permiso para guardar listas de precio.')
    })
  })
})
