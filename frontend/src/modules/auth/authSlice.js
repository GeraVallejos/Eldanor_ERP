import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '@/api/client'

function decodeJwtPayload(token) {
  try {
    const base64Payload = token.split('.')[1]
    const normalized = base64Payload.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(normalized))
  } catch {
    return null
  }
}

function buildUserFromAccessToken(accessToken, fallbackUser = null) {
  const payload = decodeJwtPayload(accessToken)

  const fallbackUsername = fallbackUser?.username || fallbackUser?.email || null
  const fallbackEmail = fallbackUser?.email || null

  if (!payload) {
    if (!fallbackUsername && !fallbackEmail) {
      return null
    }

    return {
      id: fallbackUser?.id || null,
      username: fallbackUsername,
      email: fallbackEmail,
      exp: null,
    }
  }

  const usernameFromPayload = payload.username || payload.email || fallbackUsername
  const emailFromPayload = payload.email || fallbackEmail

  return {
    id: payload.user_id || fallbackUser?.id || null,
    username: usernameFromPayload,
    email: emailFromPayload,
    exp: payload.exp,
  }
}

function normalizeErrorMessage(error, fallback) {
  const data = error?.response?.data
  const detail = data?.detail

  if (typeof detail === 'string') {
    if (/No active account found/i.test(detail)) {
      return 'Correo o contrasena incorrectos.'
    }

    if (/credentials/i.test(detail)) {
      return 'Credenciales invalidas.'
    }

    return detail
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return data.detail[0]
  }

  if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length > 0) {
    return data.non_field_errors[0]
  }

  if (Array.isArray(data?.email) && data.email.length > 0) {
    return data.email[0]
  }

  if (!error?.response) {
    return 'No pudimos conectar con el servidor. Intenta nuevamente.'
  }

  return fallback
}

const initialState = {
  accessToken: null,
  refreshToken: null,
  user: null,
  status: 'idle',
  error: null,
}

export const login = createAsyncThunk(
  'auth/login',
  async (credentials, { rejectWithValue }) => {
    try {
      const payload = {
        email: credentials.email ?? credentials.username,
        password: credentials.password,
      }

      const { data } = await api.post('/token/', payload)
      return {
        accessToken: data.access,
        refreshToken: data.refresh,
        userEmail: payload.email,
      }
    } catch (error) {
      return rejectWithValue(
        normalizeErrorMessage(error, 'No se pudo iniciar sesion.'),
      )
    }
  },
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    restoreSession: (state, action) => {
      const { accessToken, refreshToken, userEmail } = action.payload || {}

      if (!accessToken || !refreshToken) {
        return
      }

      state.accessToken = accessToken
      state.refreshToken = refreshToken
      state.user = buildUserFromAccessToken(accessToken, {
        username: userEmail,
        email: userEmail,
      })
      state.error = null
    },
    setCredentials: (state, action) => {
      const { accessToken, refreshToken, userEmail } = action.payload

      state.accessToken = accessToken
      state.refreshToken = refreshToken || state.refreshToken
      state.user = buildUserFromAccessToken(accessToken, {
        ...state.user,
        username: userEmail || state.user?.username,
        email: userEmail || state.user?.email,
      })
      state.error = null
    },
    logout: (state) => {
      state.accessToken = null
      state.refreshToken = null
      state.user = null
      state.status = 'idle'
      state.error = null
    },
    clearAuthError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.accessToken = action.payload.accessToken
        state.refreshToken = action.payload.refreshToken
        state.user = buildUserFromAccessToken(action.payload.accessToken, {
          username: action.payload.userEmail,
          email: action.payload.userEmail,
        })
      })
      .addCase(login.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload || 'Error de autenticacion.'
      })
  },
})

export const { restoreSession, setCredentials, logout, clearAuthError } = authSlice.actions

export const selectAuth = (state) => state.auth
export const selectAccessToken = (state) => state.auth.accessToken
export const selectRefreshToken = (state) => state.auth.refreshToken
export const selectAuthStatus = (state) => state.auth.status
export const selectAuthError = (state) => state.auth.error
export const selectCurrentUser = (state) => state.auth.user
export const selectIsAuthenticated = (state) => Boolean(state.auth.accessToken)

export default authSlice.reducer
