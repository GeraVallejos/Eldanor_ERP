import { configureStore } from '@reduxjs/toolkit'
import authReducer from '@/modules/auth/authSlice'
import productosReducer from '@/modules/productos/productosSlice'

export function createTestStore(preloadedState) {
  return configureStore({
    reducer: {
      auth: authReducer,
      productos: productosReducer,
    },
    preloadedState,
  })
}
