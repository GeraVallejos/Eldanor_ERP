import { configureStore } from '@reduxjs/toolkit'
import { buildReducersFromModules } from '@/store/moduleRegistry'

export const store = configureStore({
  reducer: buildReducersFromModules(),
})
