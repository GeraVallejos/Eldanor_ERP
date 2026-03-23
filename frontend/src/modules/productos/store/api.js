import { api } from '@/api/client'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function normalizePaginatedResponse(data) {
  return {
    results: normalizeListResponse(data),
    count: Number(data?.count ?? normalizeListResponse(data).length),
  }
}

export const PRODUCTOS_ENDPOINTS = {
  productos: '/productos/',
  categorias: '/categorias/',
  impuestos: '/impuestos/',
  listasPrecio: '/listas-precio/',
  listasPrecioItems: '/listas-precio-items/',
  monedas: '/monedas/',
  clientes: '/clientes/',
}

async function getList(endpoint, params) {
  const { data } = await api.get(endpoint, { params, suppressGlobalErrorToast: true })
  return normalizeListResponse(data)
}

async function getListWithCount(endpoint, params) {
  const { data } = await api.get(endpoint, { params, suppressGlobalErrorToast: true })
  return normalizePaginatedResponse(data)
}

async function getOne(endpoint, id) {
  const { data } = await api.get(`${endpoint}${id}/`, { suppressGlobalErrorToast: true })
  return data
}

async function createOne(endpoint, payload) {
  const { data } = await api.post(endpoint, payload, { suppressGlobalErrorToast: true })
  return data
}

async function updateOne(endpoint, id, payload) {
  const { data } = await api.patch(`${endpoint}${id}/`, payload, { suppressGlobalErrorToast: true })
  return data
}

async function removeOne(endpoint, id) {
  await api.delete(`${endpoint}${id}/`, { suppressGlobalErrorToast: true })
}

async function executeDetailAction(endpoint, id, action, { method = 'get', params, payload } = {}) {
  const target = `${endpoint}${id}/${action}/`
  if (method === 'post') {
    const { data } = await api.post(target, payload || {}, { suppressGlobalErrorToast: true })
    return data
  }

  const { data } = await api.get(target, { params, suppressGlobalErrorToast: true })
  return data
}

export const productosApi = {
  endpoints: PRODUCTOS_ENDPOINTS,
  normalizeListResponse,
  normalizePaginatedResponse,
  getList,
  getListWithCount,
  getOne,
  createOne,
  updateOne,
  removeOne,
  executeDetailAction,
}
