import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import ProductosListasPrecioPage from '@/modules/productos/pages/ProductosListasPrecioPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('productos/ProductosListasPrecioPage', () => {
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
})
