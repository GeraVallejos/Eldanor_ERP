import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  clientes: [],
  proveedores: [],
  contactos: [],
  status: 'idle',
  error: null,
}

const contactosSlice = createSlice({
  name: 'contactos',
  initialState,
  reducers: {
    setClientes: (state, action) => {
      state.clientes = Array.isArray(action.payload) ? action.payload : []
    },
    setProveedores: (state, action) => {
      state.proveedores = Array.isArray(action.payload) ? action.payload : []
    },
    setContactos: (state, action) => {
      state.contactos = Array.isArray(action.payload) ? action.payload : []
    },
    setContactosStatus: (state, action) => {
      state.status = action.payload || 'idle'
    },
    setContactosError: (state, action) => {
      state.error = action.payload || null
    },
    resetContactosState: () => initialState,
  },
})

export const {
  setClientes,
  setProveedores,
  setContactos,
  setContactosStatus,
  setContactosError,
  resetContactosState,
} = contactosSlice.actions

export const selectContactos = (state) => state.contactos
export const selectClientes = (state) => state.contactos.clientes
export const selectProveedores = (state) => state.contactos.proveedores
export const selectContactosItems = (state) => state.contactos.contactos
export const selectContactosStatus = (state) => state.contactos.status
export const selectContactosError = (state) => state.contactos.error

export default contactosSlice.reducer
