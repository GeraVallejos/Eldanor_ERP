import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Provider } from 'react-redux'
import './index.css'
import App from './App.jsx'
import { store } from '@/store'
import { setupApiInterceptors } from '@/api/client'
import {
  logout,
  restoreSession,
  selectAccessToken,
  selectRefreshToken,
  setCredentials,
} from '@/modules/auth/authSlice'
import {
  clearStoredSession,
  readStoredSession,
  writeStoredSession,
} from '@/modules/auth/utils/tokenStorage'

const persistedSession = readStoredSession()

if (persistedSession) {
  store.dispatch(restoreSession(persistedSession))
}

setupApiInterceptors({
  getAccessToken: () => selectAccessToken(store.getState()),
  getRefreshToken: () => selectRefreshToken(store.getState()),
  onTokenRefreshed: ({ accessToken, refreshToken }) => {
    const currentEmail = store.getState().auth.user?.email
    writeStoredSession({ accessToken, refreshToken, userEmail: currentEmail })
    store.dispatch(setCredentials({ accessToken, refreshToken, userEmail: currentEmail }))
  },
  onAuthFailed: () => {
    clearStoredSession()
    store.dispatch(logout())
  },
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>,
)
