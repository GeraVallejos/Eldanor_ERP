import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  pendingRequests: 0,
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    startGlobalLoading: (state) => {
      state.pendingRequests += 1
    },
    stopGlobalLoading: (state) => {
      state.pendingRequests = Math.max(0, state.pendingRequests - 1)
    },
    resetGlobalLoading: (state) => {
      state.pendingRequests = 0
    },
  },
})

export const { startGlobalLoading, stopGlobalLoading, resetGlobalLoading } = uiSlice.actions

export const selectIsGlobalLoading = (state) => Number(state?.ui?.pendingRequests || 0) > 0

export default uiSlice.reducer
