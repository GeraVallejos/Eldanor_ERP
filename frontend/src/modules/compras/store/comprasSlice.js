import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  ordenes: [],
  recepciones: [],
  status: 'idle',
  error: null,
}

const comprasSlice = createSlice({
  name: 'compras',
  initialState,
  reducers: {
    setOrdenes: (state, action) => {
      state.ordenes = Array.isArray(action.payload) ? action.payload : []
    },
    setRecepciones: (state, action) => {
      state.recepciones = Array.isArray(action.payload) ? action.payload : []
    },
    setComprasStatus: (state, action) => {
      state.status = action.payload || 'idle'
    },
    setComprasError: (state, action) => {
      state.error = action.payload || null
    },
    resetComprasState: () => initialState,
  },
})

export const {
  setOrdenes,
  setRecepciones,
  setComprasStatus,
  setComprasError,
  resetComprasState,
} = comprasSlice.actions

export const selectCompras = (state) => state.compras
export const selectOrdenesCompra = (state) => state.compras.ordenes
export const selectRecepcionesCompra = (state) => state.compras.recepciones
export const selectComprasStatus = (state) => state.compras.status
export const selectComprasError = (state) => state.compras.error

export default comprasSlice.reducer
