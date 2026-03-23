import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import ProductosListaPrecioDetailPage from '@/modules/productos/pages/ProductosListaPrecioDetailPage'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('productos/ProductosListaPrecioDetailPage', () => {
  beforeEach(() => {
    invalidateProductosCatalogCache()
  })

  it('muestra la cabecera y los items de la lista usando la nueva carga modular', async () => {
    server.use(
      http.get('*/listas-precio/lista-1/', async () =>
        HttpResponse.json({
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
        }),
      ),
      http.get('*/listas-precio-items/', async () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'item-1',
              lista: 'lista-1',
              producto: 'prod-1',
              producto_nombre: 'Taladro industrial',
              precio: '45990.00',
              descuento_maximo: '5.00',
            },
          ],
        }),
      ),
      http.get('*/productos/', async () =>
        HttpResponse.json({
          results: [
            {
              id: 'prod-1',
              sku: 'TAL-900',
              nombre: 'Taladro industrial',
            },
          ],
        }),
      ),
    )

    renderWithProviders(
      <Routes>
        <Route path="/productos/listas-precio/:id" element={<ProductosListaPrecioDetailPage />} />
      </Routes>,
      {
        preloadedState: {
          auth: {
            user: {
              id: 10,
              email: 'pricing@erp.test',
              permissions: ['PRODUCTOS.VER', 'PRODUCTOS.EDITAR'],
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
        initialEntries: ['/productos/listas-precio/lista-1'],
      },
    )

    expect(await screen.findByText('Mayorista Norte')).toBeInTheDocument()
    expect(screen.getByText(/Lista general \| CLP \| Normal \| Activa/i)).toBeInTheDocument()
    expect(screen.getByText('Taladro industrial')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Editar' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument()
  })
})
