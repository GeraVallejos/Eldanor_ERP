import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  pedidos: [],
  guias: [],
  facturas: [],
  notasCredito: [],
  status: 'idle',
  error: null,
}

const ventasSlice = createSlice({
  name: 'ventas',
  initialState,
  reducers: {
    setVentasStatus: (state, action) => {
      state.status = action.payload || 'idle'
    },
    setVentasError: (state, action) => {
      state.error = action.payload || null
    },
    setPedidosVenta: (state, action) => {
      state.pedidos = Array.isArray(action.payload) ? action.payload : []
    },
    setGuiasDespacho: (state, action) => {
      state.guias = Array.isArray(action.payload) ? action.payload : []
    },
    setFacturasVenta: (state, action) => {
      state.facturas = Array.isArray(action.payload) ? action.payload : []
    },
    setNotasCreditoVenta: (state, action) => {
      state.notasCredito = Array.isArray(action.payload) ? action.payload : []
    },
    resetVentasState: () => initialState,
  },
})

export const {
  setVentasStatus,
  setVentasError,
  setPedidosVenta,
  setGuiasDespacho,
  setFacturasVenta,
  setNotasCreditoVenta,
  resetVentasState,
} = ventasSlice.actions

export const selectVentas = (state) => state.ventas
export const selectVentasStatus = (state) => state.ventas.status
export const selectVentasError = (state) => state.ventas.error
export const selectPedidosVenta = (state) => state.ventas.pedidos
export const selectGuiasDespacho = (state) => state.ventas.guias
export const selectFacturasVenta = (state) => state.ventas.facturas
export const selectNotasCreditoVenta = (state) => state.ventas.notasCredito

export default ventasSlice.reducer
