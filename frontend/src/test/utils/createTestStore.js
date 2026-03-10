import { configureStore } from '@reduxjs/toolkit'
import { buildReducersFromModules } from '@/store/moduleRegistry'

export function createTestStore(preloadedState) {
  return configureStore({
    reducer: buildReducersFromModules(),
    preloadedState,
  })
}
