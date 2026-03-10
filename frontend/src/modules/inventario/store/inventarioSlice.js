import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  kardex: [],
  resumen: null,
  status: 'idle',
  error: null,
}

const inventarioSlice = createSlice({
  name: 'inventario',
  initialState,
  reducers: {
    setInventarioKardex: (state, action) => {
      state.kardex = Array.isArray(action.payload) ? action.payload : []
    },
    setInventarioResumen: (state, action) => {
      state.resumen = action.payload || null
    },
    setInventarioStatus: (state, action) => {
      state.status = action.payload || 'idle'
    },
    setInventarioError: (state, action) => {
      state.error = action.payload || null
    },
    resetInventarioState: () => initialState,
  },
})

export const {
  setInventarioKardex,
  setInventarioResumen,
  setInventarioStatus,
  setInventarioError,
  resetInventarioState,
} = inventarioSlice.actions

export const selectInventario = (state) => state.inventario
export const selectInventarioKardex = (state) => state.inventario.kardex
export const selectInventarioResumen = (state) => state.inventario.resumen
export const selectInventarioStatus = (state) => state.inventario.status
export const selectInventarioError = (state) => state.inventario.error

export default inventarioSlice.reducer
