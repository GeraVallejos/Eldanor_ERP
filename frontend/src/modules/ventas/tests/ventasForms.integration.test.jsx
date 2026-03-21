import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VentasPedidosFormPage from '@/modules/ventas/pages/VentasPedidosFormPage'
import VentasGuiasFormPage from '@/modules/ventas/pages/VentasGuiasFormPage'
import VentasFacturasFormPage from '@/modules/ventas/pages/VentasFacturasFormPage'
import VentasNotasFormPage from '@/modules/ventas/pages/VentasNotasFormPage'
import { renderWithProviders } from '@/test/utils/renderWithProviders'
import { server } from '@/test/msw/server'

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

import { toast } from 'sonner'

function authState(permissions = ['VENTAS.VER', 'VENTAS.CREAR', 'VENTAS.EDITAR']) {
  return {
    auth: {
      user: {
        id: 'user-1',
        email: 'ventas@eldanor.cl',
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

describe('ventas/forms integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('crea pedido y envia payload esperado', async () => {
    let pedidoPayload = null
    let itemPayload = null

    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1', contacto_nombre: 'Cliente 1' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/pedidos-venta/siguiente_numero/', async () => HttpResponse.json({ numero: 'PV-100' })),
      http.post('*/pedidos-venta/', async ({ request }) => {
        pedidoPayload = await request.json()
        return HttpResponse.json({ id: 'ped-1' }, { status: 201 })
      }),
      http.post('*/pedidos-venta-items/', async ({ request }) => {
        itemPayload = await request.json()
        return HttpResponse.json({ id: 'pi-1' }, { status: 201 })
      }),
    )

    renderWithProviders(<VentasPedidosFormPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.CREAR']),
      initialEntries: ['/ventas/pedidos/nuevo'],
    })

    expect(await screen.findByText('Nuevo pedido de venta')).toBeInTheDocument()

    const combos = await screen.findAllByRole('combobox')
    // Select cliente in SearchableSelect
    await userEvent.type(combos[0], 'Cliente')
    await userEvent.click(await screen.findByRole('button', { name: 'Cliente 1' }))

    // Select producto in SearchableSelect
    await userEvent.type(combos[1], 'Producto')
    await userEvent.click(await screen.findByRole('button', { name: 'Producto 1' }))

    await userEvent.click(screen.getByRole('button', { name: 'Crear pedido' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Pedido creado.')
    })

    expect(pedidoPayload).toMatchObject({
      cliente: 'cli-1',
      subtotal: 1000,
      impuestos: 0,
      total: 1000,
    })
    expect(itemPayload).toMatchObject({
      pedido_venta: 'ped-1',
      producto: 'prod-1',
      cantidad: 1,
      precio_unitario: 1000,
      subtotal: 1000,
      total: 1000,
    })
  })

  it('edita guia y envia payload esperado', async () => {
    let guiaPatchPayload = null

    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1', contacto_nombre: 'Cliente 1' }])),
      http.get('*/pedidos-venta/', async () => HttpResponse.json([{ id: 'ped-1', numero: 'PV-001' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/guias-despacho/g-1/', async () => HttpResponse.json({ id: 'g-1', numero: 'GD-001', estado: 'BORRADOR', cliente: 'cli-1', cliente_nombre: 'Cliente 1', pedido_venta: 'ped-1', fecha_despacho: '2026-03-19', observaciones: '' })),
      http.get('*/guias-despacho-items/', async () => HttpResponse.json([{ id: 'gi-1', guia_despacho: 'g-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, impuesto: 1, impuesto_porcentaje: 19 }])),
      http.patch('*/guias-despacho/g-1/', async ({ request }) => {
        guiaPatchPayload = await request.json()
        return HttpResponse.json({ id: 'g-1' })
      }),
      http.delete('*/guias-despacho-items/gi-1/', async () => HttpResponse.json({}, { status: 204 })),
      http.post('*/guias-despacho-items/', async () => HttpResponse.json({ id: 'gi-2' }, { status: 201 })),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/guias/:id/editar" element={<VentasGuiasFormPage />} />
        <Route path="/ventas/guias" element={<div>Guias redirect target</div>} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER', 'VENTAS.EDITAR']),
        initialEntries: ['/ventas/guias/g-1/editar'],
      },
    )

    expect(await screen.findByText('Editar guia')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Guia actualizada.')
    })

    expect(guiaPatchPayload).toMatchObject({
      cliente: 'cli-1',
      pedido_venta: 'ped-1',
      subtotal: 1000,
      impuestos: 190,
      total: 1190,
    })
  })

  it('crea factura y envia payload esperado', async () => {
    let facturaPayload = null
    let facturaItemPayload = null

    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1', contacto_nombre: 'Cliente 1' }])),
      http.get('*/pedidos-venta/', async () => HttpResponse.json([{ id: 'ped-1', numero: 'PV-001' }])),
      http.get('*/guias-despacho/', async () => HttpResponse.json([{ id: 'g-1', numero: 'GD-001' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/facturas-venta/siguiente_numero/', async () => HttpResponse.json({ numero: 'FV-100' })),
      http.post('*/facturas-venta/', async ({ request }) => {
        facturaPayload = await request.json()
        return HttpResponse.json({ id: 'f-1' }, { status: 201 })
      }),
      http.post('*/facturas-venta-items/', async ({ request }) => {
        facturaItemPayload = await request.json()
        return HttpResponse.json({ id: 'fi-1' }, { status: 201 })
      }),
    )

    renderWithProviders(<VentasFacturasFormPage />, {
      preloadedState: authState(['VENTAS.VER', 'VENTAS.CREAR']),
      initialEntries: ['/ventas/facturas/nuevo'],
    })

    expect(await screen.findByText('Nueva factura de venta')).toBeInTheDocument()

    // Wait for items section to be visible
    expect(await screen.findByText('Items')).toBeInTheDocument()

    // Find inputs by aria-label (more reliable than role)
    const clienteInput = await screen.findByLabelText('Cliente')
    await userEvent.type(clienteInput, 'Cliente')
    await userEvent.click(await screen.findByRole('button', { name: 'Cliente 1' }))

    // Find producto input by aria-label
    const productoInputs = await screen.findAllByLabelText(/Producto item/)
    await userEvent.type(productoInputs[0], 'Producto')
    await userEvent.click(await screen.findByRole('button', { name: 'Producto 1' }))

    await userEvent.click(screen.getByRole('button', { name: 'Crear factura' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Factura creada.')
    })

    expect(facturaPayload).toMatchObject({
      cliente: 'cli-1',
      subtotal: 1000,
      impuestos: 0,
      total: 1000,
    })
    expect(facturaItemPayload).toMatchObject({
      factura_venta: 'f-1',
      producto: 'prod-1',
      cantidad: 1,
      precio_unitario: 1000,
      subtotal: 1000,
      total: 1000,
    })
  })

  it('edita nota de credito y envia payload esperado', async () => {
    let notaPatchPayload = null

    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1', contacto_nombre: 'Cliente 1' }])),
      http.get('*/facturas-venta/', async () => HttpResponse.json([{ id: 'f-1', numero: 'FV-001' }])),
      http.get('*/facturas-venta-items/', async () => HttpResponse.json([{ id: 'fi-1', factura_venta: 'f-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/notas-credito-venta/nc-1/', async () => HttpResponse.json({ id: 'nc-1', numero: 'NC-001', estado: 'BORRADOR', cliente: 'cli-1', factura_venta: 'f-1', fecha_emision: '2026-03-19', motivo: 'Ajuste', observaciones: '' })),
      http.get('*/notas-credito-venta-items/', async () => HttpResponse.json([{ id: 'nci-1', nota_credito_venta: 'nc-1', factura_item: 'fi-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
      http.patch('*/notas-credito-venta/nc-1/', async ({ request }) => {
        notaPatchPayload = await request.json()
        return HttpResponse.json({ id: 'nc-1' })
      }),
      http.delete('*/notas-credito-venta-items/nci-1/', async () => HttpResponse.json({}, { status: 204 })),
      http.post('*/notas-credito-venta-items/', async () => HttpResponse.json({ id: 'nci-2' }, { status: 201 })),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/notas/:id/editar" element={<VentasNotasFormPage />} />
        <Route path="/ventas/notas" element={<div>Notas redirect target</div>} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER', 'VENTAS.EDITAR']),
        initialEntries: ['/ventas/notas/nc-1/editar'],
      },
    )

    expect(await screen.findByText('Editar nota de credito')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Nota de credito actualizada.')
    })

    expect(notaPatchPayload).toMatchObject({
      cliente: 'cli-1',
      factura_venta: 'f-1',
      subtotal: 1000,
      impuestos: 190,
      total: 1190,
    })
  })

  it('bloquea create de pedido cuando no tiene permiso', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/pedidos-venta/siguiente_numero/', async () => HttpResponse.json({ numero: 'PV-100' })),
    )

    renderWithProviders(<VentasPedidosFormPage />, {
      preloadedState: authState(['VENTAS.VER']),
      initialEntries: ['/ventas/pedidos/nuevo'],
    })

    expect(await screen.findByText('No tiene permiso para crear pedidos de venta.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Crear pedido' })).toBeDisabled()
  })

  it('bloquea edit de factura cuando no tiene permiso', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/pedidos-venta/', async () => HttpResponse.json([{ id: 'ped-1', numero: 'PV-001' }])),
      http.get('*/guias-despacho/', async () => HttpResponse.json([{ id: 'g-1', numero: 'GD-001' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/facturas-venta/f-1/', async () => HttpResponse.json({ id: 'f-1', numero: 'FV-001', cliente: 'cli-1', pedido_venta: 'ped-1', guia_despacho: 'g-1', fecha_emision: '2026-03-19', fecha_vencimiento: '2026-03-20', observaciones: '' })),
      http.get('*/facturas-venta-items/', async () => HttpResponse.json([{ id: 'fi-1', factura_venta: 'f-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/facturas/:id/editar" element={<VentasFacturasFormPage />} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER']),
        initialEntries: ['/ventas/facturas/f-1/editar'],
      },
    )

    expect(await screen.findByText('No tiene permiso para editar facturas de venta.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled()
  })

  it('bloquea edit de guia cuando la guia ya no esta en borrador', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/pedidos-venta/', async () => HttpResponse.json([{ id: 'ped-1', numero: 'PV-001' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/guias-despacho/g-2/', async () => HttpResponse.json({ id: 'g-2', numero: 'GD-002', estado: 'CONFIRMADA', cliente: 'cli-1', pedido_venta: 'ped-1', fecha_despacho: '2026-03-19', observaciones: '' })),
      http.get('*/guias-despacho-items/', async () => HttpResponse.json([{ id: 'gi-1', guia_despacho: 'g-2', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, impuesto: 1, impuesto_porcentaje: 19 }])),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/guias/:id/editar" element={<VentasGuiasFormPage />} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER', 'VENTAS.EDITAR']),
        initialEntries: ['/ventas/guias/g-2/editar'],
      },
    )

    expect(await screen.findByText('Solo se pueden editar guias en estado BORRADOR.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled()
  })

  it('bloquea create de guia cuando no tiene permiso', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/pedidos-venta/', async () => HttpResponse.json([{ id: 'ped-1', numero: 'PV-001' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/guias-despacho/siguiente_numero/', async () => HttpResponse.json({ numero: 'GD-100' })),
    )

    renderWithProviders(<VentasGuiasFormPage />, {
      preloadedState: authState(['VENTAS.VER']),
      initialEntries: ['/ventas/guias/nuevo'],
    })

    expect(await screen.findByText('No tiene permiso para crear guias de despacho.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Crear guia' })).toBeDisabled()
  })

  it('bloquea edit de nota de credito cuando no tiene permiso', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/facturas-venta/', async () => HttpResponse.json([{ id: 'f-1', numero: 'FV-001' }])),
      http.get('*/facturas-venta-items/', async () => HttpResponse.json([{ id: 'fi-1', factura_venta: 'f-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/notas-credito-venta/nc-1/', async () => HttpResponse.json({ id: 'nc-1', numero: 'NC-001', cliente: 'cli-1', factura_venta: 'f-1', fecha_emision: '2026-03-19', motivo: 'Ajuste', observaciones: '' })),
      http.get('*/notas-credito-venta-items/', async () => HttpResponse.json([{ id: 'nci-1', nota_credito_venta: 'nc-1', factura_item: 'fi-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/notas/:id/editar" element={<VentasNotasFormPage />} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER']),
        initialEntries: ['/ventas/notas/nc-1/editar'],
      },
    )

    expect(await screen.findByText('No tiene permiso para editar notas de credito.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled()
  })

  it('bloquea edit de factura emitida aunque el usuario tenga permiso', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/pedidos-venta/', async () => HttpResponse.json([{ id: 'ped-1', numero: 'PV-001' }])),
      http.get('*/guias-despacho/', async () => HttpResponse.json([{ id: 'g-1', numero: 'GD-001' }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/impuestos/', async () => HttpResponse.json([{ id: 1, nombre: 'IVA', porcentaje: 19 }])),
      http.get('*/facturas-venta/f-2/', async () => HttpResponse.json({ id: 'f-2', numero: 'FV-002', estado: 'EMITIDA', cliente: 'cli-1', pedido_venta: 'ped-1', guia_despacho: 'g-1', fecha_emision: '2026-03-19', fecha_vencimiento: '2026-03-20', observaciones: '' })),
      http.get('*/facturas-venta-items/', async () => HttpResponse.json([{ id: 'fi-1', factura_venta: 'f-2', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/facturas/:id/editar" element={<VentasFacturasFormPage />} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER', 'VENTAS.EDITAR']),
        initialEntries: ['/ventas/facturas/f-2/editar'],
      },
    )

    expect(await screen.findByText('Solo se pueden editar facturas en estado BORRADOR.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled()
  })

  it('bloquea edit de nota emitida aunque el usuario tenga permiso', async () => {
    server.use(
      http.get('*/clientes/', async () => HttpResponse.json([{ id: 'cli-1', nombre: 'Cliente 1' }])),
      http.get('*/facturas-venta/', async () => HttpResponse.json([{ id: 'f-1', numero: 'FV-001' }])),
      http.get('*/facturas-venta-items/', async () => HttpResponse.json([{ id: 'fi-1', factura_venta: 'f-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
      http.get('*/productos/', async () => HttpResponse.json([{ id: 'prod-1', nombre: 'Producto 1', precio_referencia: 1000, impuesto: 1 }])),
      http.get('*/notas-credito-venta/nc-2/', async () => HttpResponse.json({ id: 'nc-2', numero: 'NC-002', estado: 'EMITIDA', cliente: 'cli-1', factura_venta: 'f-1', fecha_emision: '2026-03-19', motivo: 'Ajuste', observaciones: '' })),
      http.get('*/notas-credito-venta-items/', async () => HttpResponse.json([{ id: 'nci-1', nota_credito_venta: 'nc-2', factura_item: 'fi-1', producto: 'prod-1', descripcion: 'Producto 1', cantidad: 1, precio_unitario: 1000, descuento: 0, impuesto: 1, impuesto_porcentaje: 19 }])),
    )

    renderWithProviders(
      <Routes>
        <Route path="/ventas/notas/:id/editar" element={<VentasNotasFormPage />} />
      </Routes>,
      {
        preloadedState: authState(['VENTAS.VER', 'VENTAS.EDITAR']),
        initialEntries: ['/ventas/notas/nc-2/editar'],
      },
    )

    expect(await screen.findByText('Solo se pueden editar notas de credito en estado BORRADOR.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled()
  })
})
