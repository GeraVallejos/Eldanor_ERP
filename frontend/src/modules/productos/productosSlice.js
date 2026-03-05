import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import { api } from '@/api/client'
import { login, logout } from '@/modules/auth/authSlice'

function normalizeProductsResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function normalizeErrorMessage(error, fallback) {
  const data = error?.response?.data

  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (Array.isArray(data?.detail) && data.detail.length > 0) {
    return data.detail[0]
  }

  if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length > 0) {
    return data.non_field_errors[0]
  }

  return fallback
}

function normalizeCatalogResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

const initialState = {
  items: [],
  status: 'idle',
  error: null,
  createStatus: 'idle',
  createError: null,
  categorias: [],
  impuestos: [],
  catalogStatus: 'idle',
  catalogError: null,
}

export const fetchProductos = createAsyncThunk(
  'productos/fetchProductos',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get('/productos/')
      return normalizeProductsResponse(data)
    } catch (error) {
      return rejectWithValue(
        normalizeErrorMessage(error, 'No se pudo cargar productos.'),
      )
    }
  },
)

export const fetchCatalogosProducto = createAsyncThunk(
  'productos/fetchCatalogosProducto',
  async (_, { rejectWithValue }) => {
    try {
      const [{ data: categoriasData }, { data: impuestosData }] = await Promise.all([
        api.get('/categorias/'),
        api.get('/impuestos/'),
      ])

      return {
        categorias: normalizeCatalogResponse(categoriasData),
        impuestos: normalizeCatalogResponse(impuestosData),
      }
    } catch (error) {
      return rejectWithValue(
        normalizeErrorMessage(error, 'No se pudieron cargar categorias e impuestos.'),
      )
    }
  },
)

export const createProducto = createAsyncThunk(
  'productos/createProducto',
  async (payload, { rejectWithValue }) => {
    try {
      const { data } = await api.post('/productos/', payload)
      return data
    } catch (error) {
      return rejectWithValue(
        normalizeErrorMessage(error, 'No se pudo crear el producto.'),
      )
    }
  },
)

const productosSlice = createSlice({
  name: 'productos',
  initialState,
  reducers: {
    clearProductosState: (state) => {
      state.items = []
      state.status = 'idle'
      state.error = null
      state.createStatus = 'idle'
      state.createError = null
    },
    resetCreateProductoState: (state) => {
      state.createStatus = 'idle'
      state.createError = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchProductos.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchProductos.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
      })
      .addCase(fetchProductos.rejected, (state, action) => {
        state.items = []
        state.status = 'failed'
        state.error = action.payload || 'Error al cargar productos.'
      })
      .addCase(fetchCatalogosProducto.pending, (state) => {
        state.catalogStatus = 'loading'
        state.catalogError = null
      })
      .addCase(fetchCatalogosProducto.fulfilled, (state, action) => {
        state.catalogStatus = 'succeeded'
        state.catalogError = null
        state.categorias = action.payload.categorias
        state.impuestos = action.payload.impuestos
      })
      .addCase(fetchCatalogosProducto.rejected, (state, action) => {
        state.catalogStatus = 'failed'
        state.catalogError = action.payload || 'Error al cargar catalogos.'
      })
      .addCase(createProducto.pending, (state) => {
        state.createStatus = 'loading'
        state.createError = null
      })
      .addCase(createProducto.fulfilled, (state, action) => {
        state.createStatus = 'succeeded'
        state.createError = null
        state.items = [action.payload, ...state.items]
      })
      .addCase(createProducto.rejected, (state, action) => {
        state.createStatus = 'failed'
        state.createError = action.payload || 'Error al crear producto.'
      })
      .addCase(login.fulfilled, (state) => {
        state.items = []
        state.status = 'idle'
        state.error = null
        state.createStatus = 'idle'
        state.createError = null
        state.categorias = []
        state.impuestos = []
        state.catalogStatus = 'idle'
        state.catalogError = null
      })
      .addCase(logout, (state) => {
        state.items = []
        state.status = 'idle'
        state.error = null
        state.createStatus = 'idle'
        state.createError = null
        state.categorias = []
        state.impuestos = []
        state.catalogStatus = 'idle'
        state.catalogError = null
      })
  },
})

export const { clearProductosState, resetCreateProductoState } = productosSlice.actions

export const selectProductos = (state) => state.productos.items
export const selectProductosStatus = (state) => state.productos.status
export const selectProductosError = (state) => state.productos.error
export const selectCreateProductoStatus = (state) => state.productos.createStatus
export const selectCreateProductoError = (state) => state.productos.createError
export const selectCategorias = (state) => state.productos.categorias
export const selectImpuestos = (state) => state.productos.impuestos
export const selectCatalogStatus = (state) => state.productos.catalogStatus
export const selectCatalogError = (state) => state.productos.catalogError

export default productosSlice.reducer
