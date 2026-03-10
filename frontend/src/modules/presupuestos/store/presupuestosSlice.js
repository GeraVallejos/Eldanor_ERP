import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  items: [],
  current: null,
  status: 'idle',
  error: null,
}

const presupuestosSlice = createSlice({
  name: 'presupuestos',
  initialState,
  reducers: {
    setPresupuestos: (state, action) => {
      state.items = Array.isArray(action.payload) ? action.payload : []
    },
    setCurrentPresupuesto: (state, action) => {
      state.current = action.payload || null
    },
    setPresupuestosStatus: (state, action) => {
      state.status = action.payload || 'idle'
    },
    setPresupuestosError: (state, action) => {
      state.error = action.payload || null
    },
    resetPresupuestosState: () => initialState,
  },
})

export const {
  setPresupuestos,
  setCurrentPresupuesto,
  setPresupuestosStatus,
  setPresupuestosError,
  resetPresupuestosState,
} = presupuestosSlice.actions

export const selectPresupuestosState = (state) => state.presupuestos
export const selectPresupuestos = (state) => state.presupuestos.items
export const selectCurrentPresupuesto = (state) => state.presupuestos.current
export const selectPresupuestosStatus = (state) => state.presupuestos.status
export const selectPresupuestosError = (state) => state.presupuestos.error

export default presupuestosSlice.reducer
