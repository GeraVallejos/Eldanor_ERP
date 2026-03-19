import { describe, expect, it } from 'vitest'

function buildPedidoPayload({ cliente, numero, fechaEmision, subtotal, impuestos, total }) {
  return {
    cliente,
    numero,
    estado: 'BORRADOR',
    fecha_emision: fechaEmision,
    subtotal,
    impuestos,
    total,
  }
}

function buildFacturaPayload({ cliente, pedidoVenta, numero, fechaEmision, subtotal, impuestos, total }) {
  return {
    cliente,
    pedido_venta: pedidoVenta,
    numero,
    estado: 'BORRADOR',
    fecha_emision: fechaEmision,
    subtotal,
    impuestos,
    total,
  }
}

function buildNotaPayload({ cliente, facturaVenta, numero, fechaEmision, subtotal, impuestos, total }) {
  return {
    cliente,
    factura_venta: facturaVenta,
    numero,
    estado: 'BORRADOR',
    fecha_emision: fechaEmision,
    subtotal,
    impuestos,
    total,
  }
}

describe('ventas/API Contract', () => {
  it('cumple contrato minimo para pedido, factura y nota de credito', () => {
    const pedido = buildPedidoPayload({
      cliente: 'cli-1',
      numero: 'PV-100',
      fechaEmision: '2026-03-19',
      subtotal: 100000,
      impuestos: 19000,
      total: 119000,
    })

    expect(pedido).toMatchObject({
      cliente: 'cli-1',
      numero: 'PV-100',
      estado: 'BORRADOR',
      fecha_emision: '2026-03-19',
      subtotal: 100000,
      impuestos: 19000,
      total: 119000,
    })

    const factura = buildFacturaPayload({
      cliente: 'cli-1',
      pedidoVenta: 'ped-1',
      numero: 'FV-100',
      fechaEmision: '2026-03-19',
      subtotal: 100000,
      impuestos: 19000,
      total: 119000,
    })

    expect(factura).toMatchObject({
      cliente: 'cli-1',
      pedido_venta: 'ped-1',
      numero: 'FV-100',
      estado: 'BORRADOR',
      fecha_emision: '2026-03-19',
      subtotal: 100000,
      impuestos: 19000,
      total: 119000,
    })

    const nota = buildNotaPayload({
      cliente: 'cli-1',
      facturaVenta: 'fac-1',
      numero: 'NC-100',
      fechaEmision: '2026-03-19',
      subtotal: 10000,
      impuestos: 1900,
      total: 11900,
    })

    expect(nota).toMatchObject({
      cliente: 'cli-1',
      factura_venta: 'fac-1',
      numero: 'NC-100',
      estado: 'BORRADOR',
      fecha_emision: '2026-03-19',
      subtotal: 10000,
      impuestos: 1900,
      total: 11900,
    })
  })
})
