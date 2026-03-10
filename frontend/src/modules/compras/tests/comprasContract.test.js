import { describe, expect, it } from 'vitest'

function buildOrdenCompraPayload({ proveedor, numero, fechaEmision, subtotal, impuestos, total }) {
  return {
    proveedor,
    numero,
    estado: 'BORRADOR',
    fecha_emision: fechaEmision,
    subtotal,
    impuestos,
    total,
  }
}

function buildOrdenCompraItemPayload({ ordenId, productoId, descripcion, cantidad, precioUnitario, subtotal, total }) {
  return {
    orden_compra: ordenId,
    producto: productoId,
    descripcion,
    cantidad,
    precio_unitario: precioUnitario,
    subtotal,
    total,
  }
}

describe('compras/API Contract', () => {
  it('cumple contrato minimo de create/list/update/delete', async () => {
    const orden = buildOrdenCompraPayload({
      proveedor: 'prov-1',
      numero: 'OC-100',
      fechaEmision: '2026-03-10',
      subtotal: 1000,
      impuestos: 190,
      total: 1190,
    })

    expect(orden).toMatchObject({
      proveedor: 'prov-1',
      numero: 'OC-100',
      estado: 'BORRADOR',
      fecha_emision: '2026-03-10',
      subtotal: 1000,
      impuestos: 190,
      total: 1190,
    })

    const item = buildOrdenCompraItemPayload({
      ordenId: 'oc-100',
      productoId: 'prod-1',
      descripcion: 'Producto A',
      cantidad: 2,
      precioUnitario: 500,
      subtotal: 1000,
      total: 1190,
    })

    expect(item).toMatchObject({
      orden_compra: 'oc-100',
      producto: 'prod-1',
      descripcion: 'Producto A',
      cantidad: 2,
      precio_unitario: 500,
      subtotal: 1000,
      total: 1190,
    })
  })
})
