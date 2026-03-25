import inventarioReducer from '@/modules/inventario/store/inventarioSlice'

export const inventarioStoreModule = {
  key: 'inventario',
  reducer: inventarioReducer,
}

export { inventarioApi } from '@/modules/inventario/store/api'
export { useInventarioHistorial, useMovimientoAuditoria } from '@/modules/inventario/store/hooks'
