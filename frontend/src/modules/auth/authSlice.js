import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'

const initialState = {
  user: null,
  empresas: [],
  empresasStatus: 'idle',
  empresasError: null,
  changingEmpresaId: null,
  isAuthenticated: false,
  status: 'idle',
  bootstrapStatus: 'idle',
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

      const { data } = await api.post('/token/', payload, {
        suppressGlobalErrorToast: true,
      })
      return data?.user
    } catch (error) {
      return rejectWithValue(
        normalizeApiError(error, {
          fallback: 'No se pudo iniciar sesion.',
          transformDetail: (detail) => {
            if (/No active account found/i.test(detail)) {
              return 'Correo o contrasena incorrectos.'
            }

            if (/credentials/i.test(detail)) {
              return 'Credenciales invalidas.'
            }

            return detail
          },
        }),
      )
    }
  },
)

export const bootstrapSession = createAsyncThunk(
  'auth/bootstrapSession',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get('/auth/me/', {
        suppressGlobalErrorToast: true,
      })
      return data?.user
    } catch (error) {
      return rejectWithValue(error?.response?.status || 401)
    }
  },
)

export const logoutUser = createAsyncThunk('auth/logoutUser', async () => {
  await api.post('/auth/logout/', undefined, {
    suppressGlobalErrorToast: true,
  })
})

export const fetchEmpresasUsuario = createAsyncThunk(
  'auth/fetchEmpresasUsuario',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get('/empresas-usuario/', {
        suppressGlobalErrorToast: true,
      })
      return Array.isArray(data) ? data : []
    } catch (error) {
      return rejectWithValue(
        normalizeApiError(error, { fallback: 'No se pudieron cargar las empresas.' }),
      )
    }
  },
)

export const changeEmpresaActiva = createAsyncThunk(
  'auth/changeEmpresaActiva',
  async (empresaId, { dispatch, rejectWithValue }) => {
    try {
      await api.post(
        '/cambiar-empresa-activa/',
        { empresa_id: empresaId },
        { suppressGlobalErrorToast: true },
      )
      await dispatch(bootstrapSession()).unwrap()
      await dispatch(fetchEmpresasUsuario()).unwrap()
      return empresaId
    } catch (error) {
      return rejectWithValue(
        normalizeApiError(error, { fallback: 'No se pudo cambiar la empresa activa.' }),
      )
    }
  },
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.user = null
      state.empresas = []
      state.empresasStatus = 'idle'
      state.empresasError = null
      state.changingEmpresaId = null
      state.isAuthenticated = false
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
        state.user = action.payload || null
        state.isAuthenticated = Boolean(action.payload)
        state.error = null
      })
      .addCase(login.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload || 'Error de autenticacion.'
      })
      .addCase(bootstrapSession.pending, (state) => {
        state.bootstrapStatus = 'loading'
      })
      .addCase(bootstrapSession.fulfilled, (state, action) => {
        state.bootstrapStatus = 'succeeded'
        state.user = action.payload || null
        state.isAuthenticated = Boolean(action.payload)
      })
      .addCase(bootstrapSession.rejected, (state) => {
        state.bootstrapStatus = 'failed'
        state.user = null
        state.isAuthenticated = false
      })
      .addCase(logoutUser.fulfilled, (state) => {
        state.user = null
        state.empresas = []
        state.empresasStatus = 'idle'
        state.empresasError = null
        state.changingEmpresaId = null
        state.isAuthenticated = false
        state.status = 'idle'
        state.error = null
      })
      .addCase(fetchEmpresasUsuario.pending, (state) => {
        state.empresasStatus = 'loading'
        state.empresasError = null
      })
      .addCase(fetchEmpresasUsuario.fulfilled, (state, action) => {
        state.empresasStatus = 'succeeded'
        state.empresas = action.payload
      })
      .addCase(fetchEmpresasUsuario.rejected, (state, action) => {
        state.empresasStatus = 'failed'
        state.empresas = []
        state.empresasError = action.payload || 'Error al cargar empresas.'
      })
      .addCase(changeEmpresaActiva.pending, (state, action) => {
        state.changingEmpresaId = action.meta.arg || null
      })
      .addCase(changeEmpresaActiva.fulfilled, (state) => {
        state.changingEmpresaId = null
      })
      .addCase(changeEmpresaActiva.rejected, (state, action) => {
        state.changingEmpresaId = null
        state.empresasError = action.payload || 'Error al cambiar empresa.'
      })
  },
})

export const { logout, clearAuthError } = authSlice.actions

export const selectAuth = (state) => state.auth
export const selectAuthStatus = (state) => state.auth.status
export const selectAuthBootstrapStatus = (state) => state.auth.bootstrapStatus
export const selectAuthError = (state) => state.auth.error
export const selectCurrentUser = (state) => state.auth.user
export const selectEmpresasUsuario = (state) => state.auth.empresas
export const selectEmpresasStatus = (state) => state.auth.empresasStatus
export const selectEmpresasError = (state) => state.auth.empresasError
export const selectChangingEmpresaId = (state) => state.auth.changingEmpresaId
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated

export default authSlice.reducer
