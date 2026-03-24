import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ProductosAnalisisPage from '@/modules/productos/pages/ProductosAnalisisPage'
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
      http.get('*/productos/prod-1/gobernanza/', async () =>
        HttpResponse.json({
          producto_id: 'prod-1',
          score: 72,
          estado: 'OBSERVADO',
          readiness: {
            ventas: true,
            inventario: false,
            compliance: true,
          },
          hallazgos: [
            {
              codigo: 'GOB_STOCK_MINIMO_NO_DEFINIDO',
              dimension: 'inventario',
              nivel: 'warning',
              detalle: 'El producto inventariable no tiene stock minimo configurado.',
              impacto: -10,
            },
          ],
          metricas: {
            listas_vigentes: 1,
            pedidos_venta: 1,
            documentos_compra: 1,
          },
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
    expect(screen.getByText('$ 31.000')).toBeInTheDocument()
    expect(screen.getByText('Score 72')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver analisis' })).toBeInTheDocument()
    expect(screen.queryByText('Gobernanza del maestro')).not.toBeInTheDocument()
    expect(screen.queryByText('Historial del maestro')).not.toBeInTheDocument()
    expect(screen.queryByText('Versiones del maestro')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a inventario' })).toBeInTheDocument()
  })

  it('muestra acceso a editar cuando el usuario tiene permiso', async () => {
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
      http.get('*/productos/prod-1/gobernanza/', async () =>
        HttpResponse.json({
          producto_id: 'prod-1',
          score: 100,
          estado: 'LISTO',
          readiness: {
            ventas: true,
            inventario: true,
            compliance: true,
          },
          hallazgos: [],
          metricas: {
            listas_vigentes: 1,
            pedidos_venta: 0,
            documentos_compra: 0,
          },
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
              email: 'editor@erp.test',
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
        initialEntries: ['/productos/prod-1'],
      },
    )

    expect(await screen.findByText('Taladro industrial')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Editar' })).toHaveAttribute('href', '/productos/prod-1/editar')
  })

  it('mueve la informacion avanzada a la pantalla de analisis', async () => {
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
      http.get('*/productos/prod-1/historial/', async () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 'audit-1',
              action_code: 'EDITAR',
              event_type: 'PRODUCTO_ACTUALIZADO',
              severity: 'INFO',
              summary: 'Producto actualizado por cambio comercial.',
              changes: {
                precio_referencia: ['42000', '45990'],
                impuesto_id: [null, 'imp-1'],
              },
              payload: { producto_id: 'prod-1' },
              creado_por: 10,
              creado_por_email: 'viewer@erp.test',
              occurred_at: '2026-03-21T10:30:00Z',
            },
          ],
        }),
      ),
      http.get('*/productos/prod-1/gobernanza/', async () =>
        HttpResponse.json({
          producto_id: 'prod-1',
          score: 72,
          estado: 'OBSERVADO',
          readiness: {
            ventas: true,
            inventario: false,
            compliance: true,
          },
          hallazgos: [
            {
              codigo: 'GOB_STOCK_MINIMO_NO_DEFINIDO',
              dimension: 'inventario',
              nivel: 'warning',
              detalle: 'El producto inventariable no tiene stock minimo configurado.',
              impacto: -10,
            },
          ],
          metricas: {
            listas_vigentes: 1,
            pedidos_venta: 1,
            documentos_compra: 1,
          },
        }),
      ),
      http.get('*/productos/prod-1/versiones/', async () =>
        HttpResponse.json({
          count: 2,
          next: null,
          previous: null,
          results: [
            {
              id: 'snap-3',
              producto: 'prod-1',
              producto_id_ref: 'prod-1',
              version: 3,
              event_type: 'producto.actualizado',
              changes: {
                activo: ['False', 'True'],
              },
              snapshot: {
                precio_referencia: '47990.00',
                activo: 'True',
              },
              creado_por: 10,
              creado_por_email: 'viewer@erp.test',
              creado_en: '2026-03-22T09:00:00Z',
            },
            {
              id: 'snap-2',
              producto: 'prod-1',
              producto_id_ref: 'prod-1',
              version: 2,
              event_type: 'producto.actualizado',
              changes: {
                precio_referencia: ['42000', '45990'],
              },
              snapshot: {
                precio_referencia: '45990.00',
                activo: 'True',
              },
              creado_por: 10,
              creado_por_email: 'viewer@erp.test',
              creado_en: '2026-03-21T11:00:00Z',
            },
          ],
        }),
      ),
    )

    renderWithProviders(
      <Routes>
        <Route path="/productos/:id/analisis" element={<ProductosAnalisisPage />} />
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
        initialEntries: ['/productos/prod-1/analisis'],
      },
    )

    expect(await screen.findByText('Gobernanza del maestro')).toBeInTheDocument()
    expect(screen.getByText('Historial del maestro')).toBeInTheDocument()
    expect(screen.getByText('Versiones del maestro')).toBeInTheDocument()
    expect(screen.getByText('Uso en documentos')).toBeInTheDocument()
    expect(screen.getByText('GOB_STOCK_MINIMO_NO_DEFINIDO')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Comparar' })).toBeInTheDocument()
    expect(screen.getByText('Producto actualizado por cambio comercial.')).toBeInTheDocument()
    expect(screen.getAllByText('Version 2').length).toBeGreaterThan(0)
    expect(
      screen.getAllByText((_, element) => String(element?.textContent || '').includes('Constructora Norte')).length,
    ).toBeGreaterThan(0)
    expect(screen.getByText(/Pedidos de venta recientes \(1\)/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Version actual' })).not.toBeInTheDocument()
  })
})
