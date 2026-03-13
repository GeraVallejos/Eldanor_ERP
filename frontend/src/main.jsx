import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import { Toaster } from 'sonner'
import './index.css'
import App from './App.jsx'
import { store } from '@/store'
import { setupApiInterceptors } from '@/api/client'
import {
  bootstrapSession,
  logout,
} from '@/modules/auth/authSlice'
import { startGlobalLoading, stopGlobalLoading } from '@/modules/shared/ui/uiSlice'

setupApiInterceptors({
  onAuthFailed: () => {
    store.dispatch(logout())
  },
  onRequestStart: () => {
    store.dispatch(startGlobalLoading())
  },
  onRequestEnd: () => {
    store.dispatch(stopGlobalLoading())
  },
})

store.dispatch(bootstrapSession())

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Provider store={store}>
      <App />
      <Toaster richColors position="top-right" />
    </Provider>
  </StrictMode>,
)
