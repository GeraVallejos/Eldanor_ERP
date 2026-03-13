import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  eventos: [],
  pagination: {
    count: 0,
    next: null,
    previous: null,
  },
  filters: {
    module_code: '',
    action_code: '',
    event_type: '',
    entity_type: '',
    severity: '',
    date_from: '',
    date_to: '',
    page: 1,
    page_size: 8,
  },
  submittedFilters: {
    module_code: '',
    action_code: '',
    event_type: '',
    entity_type: '',
    severity: '',
    date_from: '',
    date_to: '',
    page: 1,
    page_size: 8,
  },
  detalleEvento: null,
  detalleStatus: 'idle',
  detalleError: null,
  integrity: null,
  status: 'idle',
  error: null,
}

const auditoriaSlice = createSlice({
  name: 'auditoria',
  initialState,
  reducers: {
    setAuditoriaEventos: (state, action) => {
      state.eventos = Array.isArray(action.payload) ? action.payload : []
    },
    setAuditoriaPagination: (state, action) => {
      const next = action.payload || {}
      state.pagination = {
        count: Number(next.count || 0),
        next: next.next || null,
        previous: next.previous || null,
      }
    },
    setAuditoriaFilters: (state, action) => {
      state.filters = {
        ...state.filters,
        ...(action.payload || {}),
      }
    },
    setAuditoriaSubmittedFilters: (state, action) => {
      state.submittedFilters = {
        ...state.submittedFilters,
        ...(action.payload || {}),
      }
    },
    clearAuditoriaFilters: (state) => {
      const keptPageSize = state.filters.page_size || initialState.filters.page_size
      const nextFilters = {
        ...initialState.filters,
        page_size: keptPageSize,
      }
      state.filters = nextFilters
      state.submittedFilters = { ...nextFilters }
    },
    setAuditoriaIntegrity: (state, action) => {
      state.integrity = action.payload || null
    },
    setAuditoriaDetalleEvento: (state, action) => {
      state.detalleEvento = action.payload || null
    },
    setAuditoriaDetalleStatus: (state, action) => {
      state.detalleStatus = action.payload || 'idle'
    },
    setAuditoriaDetalleError: (state, action) => {
      state.detalleError = action.payload || null
    },
    setAuditoriaStatus: (state, action) => {
      state.status = action.payload || 'idle'
    },
    setAuditoriaError: (state, action) => {
      state.error = action.payload || null
    },
    resetAuditoriaState: () => initialState,
  },
})

export const {
  setAuditoriaEventos,
  setAuditoriaPagination,
  setAuditoriaFilters,
  setAuditoriaSubmittedFilters,
  clearAuditoriaFilters,
  setAuditoriaIntegrity,
  setAuditoriaDetalleEvento,
  setAuditoriaDetalleStatus,
  setAuditoriaDetalleError,
  setAuditoriaStatus,
  setAuditoriaError,
  resetAuditoriaState,
} = auditoriaSlice.actions

export const selectAuditoria = (state) => state.auditoria
export const selectAuditoriaEventos = (state) => state.auditoria.eventos
export const selectAuditoriaPagination = (state) => state.auditoria.pagination
export const selectAuditoriaFilters = (state) => state.auditoria.filters
export const selectAuditoriaSubmittedFilters = (state) => state.auditoria.submittedFilters
export const selectAuditoriaIntegrity = (state) => state.auditoria.integrity
export const selectAuditoriaDetalleEvento = (state) => state.auditoria.detalleEvento
export const selectAuditoriaDetalleStatus = (state) => state.auditoria.detalleStatus
export const selectAuditoriaDetalleError = (state) => state.auditoria.detalleError
export const selectAuditoriaStatus = (state) => state.auditoria.status
export const selectAuditoriaError = (state) => state.auditoria.error

export default auditoriaSlice.reducer