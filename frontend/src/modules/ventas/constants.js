export const VENTAS_ENDPOINTS = {
  pedidos: '/pedidos-venta/',
  pedidosItems: '/pedidos-venta-items/',
  guias: '/guias-despacho/',
  guiasItems: '/guias-despacho-items/',
  facturas: '/facturas-venta/',
  facturasItems: '/facturas-venta-items/',
  notas: '/notas-credito-venta/',
  notasItems: '/notas-credito-venta-items/',
}

export const VENTAS_ESTADOS = {
  pedido: ['BORRADOR', 'CONFIRMADO', 'EN_PROCESO', 'DESPACHADO', 'FACTURADO', 'ANULADO'],
  guia: ['BORRADOR', 'CONFIRMADA', 'ANULADA'],
  factura: ['BORRADOR', 'EMITIDA', 'ANULADA'],
  nota: ['BORRADOR', 'EMITIDA', 'ANULADA'],
}

export const VENTAS_PERMISSIONS = {
  ver: 'VENTAS.VER',
  crear: 'VENTAS.CREAR',
  editar: 'VENTAS.EDITAR',
  aprobar: 'VENTAS.APROBAR',
  anular: 'VENTAS.ANULAR',
  borrar: 'VENTAS.BORRAR',
}
