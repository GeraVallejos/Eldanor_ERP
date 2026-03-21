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
      http.get('*/productos/prod-1/trazabilidad/', async () =>
        HttpResponse.json({
          producto_id: 'prod-1',
          fecha_referencia: '2026-03-21',
          resumen: {
            listas_configuradas: 1,
            listas_activas_vigentes: 1,
            pedidos_venta: 1,
            documentos_compra: 1,
          },
          listas_precio: [
            {
              id: 'lista-1',
              nombre: 'Lista Cliente Norte',
              cliente_nombre: 'Constructora Norte',
              moneda_codigo: 'CLP',
              precio: '44990.00',
              descuento_maximo: '5.00',
              fecha_desde: '2026-03-01',
              fecha_hasta: null,
              activa: true,
              prioridad: 10,
              esta_vigente: true,
            },
          ],
          uso_documentos: {
            pedidos_venta: {
              cantidad: 1,
              ultimos: [
                {
                  id: 'pv-1',
                  numero: 'PV-001',
                  estado: 'CONFIRMADO',
                  fecha_emision: '2026-03-20',
                  cliente_nombre: 'Constructora Norte',
                  lista_precio_nombre: 'Lista Cliente Norte',
                  cantidad: '2.00',
                  precio_unitario: '44990.00',
                },
              ],
            },
            documentos_compra: {
              cantidad: 1,
              ultimos: [
                {
                  id: 'dc-1',
                  tipo_documento: 'FACTURA_COMPRA',
                  folio: '1234',
                  estado: 'CONFIRMADO',
                  fecha_emision: '2026-03-18',
                  proveedor_nombre: 'Proveedor Industrial',
                  cantidad: '4.00',
                  precio_unitario: '32000.00',
                },
              ],
            },
          },
          alertas: [
            {
              codigo: 'SIN_STOCK_MINIMO',
              nivel: 'warning',
              detalle: 'El producto maneja inventario, pero no tiene stock minimo definido.',
            },
          ],
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
    expect(screen.getByText('Trazabilidad comercial')).toBeInTheDocument()
    expect(screen.getByText('Lista Cliente Norte')).toBeInTheDocument()
    expect(screen.getByText(/Pedidos de venta recientes \(1\)/i)).toBeInTheDocument()
    expect(screen.getByText('SIN_STOCK_MINIMO')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a inventario' })).toBeInTheDocument()
  })
})
