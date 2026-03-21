import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ProductosDetailPage from '@/modules/productos/pages/ProductosDetailPage'
import { server } from '@/test/msw/server'
import { renderWithProviders } from '@/test/utils/renderWithProviders'

describe('productos/ProductosDetailPage', () => {
  it('muestra el resumen del producto y marca stock como informativo', async () => {
    server.use(
      http.get('*/productos/prod-1/', async () =>
        HttpResponse.json({
          id: 'prod-1',
          nombre: 'Taladro industrial',
          sku: 'TAL-900',
          tipo: 'PRODUCTO',
          activo: true,
          categoria_nombre: 'Ferreteria',
          impuesto_nombre: 'IVA',
          moneda_codigo: 'CLP',
          unidad_medida: 'UN',
          precio_referencia: 45990,
          precio_costo: 32000,
          descripcion: 'Equipo de uso profesional.',
          maneja_inventario: true,
          permite_decimales: false,
          usa_lotes: false,
          usa_series: true,
          usa_vencimiento: false,
          stock_minimo: '3.00',
          stock_actual: '8.00',
          costo_promedio: '31000.0000',
        }),
      ),
    )

    renderWithProviders(
      <Routes>
        <Route path="/productos/:id" element={<ProductosDetailPage />} />
      </Routes>,
      {
      preloadedState: {
        auth: {
          user: {
            id: 10,
            email: 'viewer@erp.test',
            permissions: ['PRODUCTOS.VER', 'INVENTARIO.VER'],
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
      initialEntries: ['/productos/prod-1'],
      },
    )

    expect(await screen.findByText('Taladro industrial')).toBeInTheDocument()
    expect(screen.getByText(/El stock actual y el costo promedio se administran desde inventario/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a inventario' })).toBeInTheDocument()
  })
})
