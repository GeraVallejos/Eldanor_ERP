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
    next: data?.next ?? null,
    previous: data?.previous ?? null,
  }
}

export const INVENTARIO_ENDPOINTS = {
  bodegas: '/bodegas/',
  stocks: '/stocks/',
  stockResumen: '/stocks/resumen/',
  stockCriticos: '/stocks/criticos/',
  stockAnalytics: '/stocks/analytics/',
  stockReconciliation: '/stocks/reconciliation/',
  movimientos: '/movimientos-inventario/',
  movimientosKardex: '/movimientos-inventario/kardex/',
  movimientosHistorial: '/movimientos-inventario/historial/',
  movimientosResumen: '/movimientos-inventario/resumen_operativo/',
  movimientosPreviewRegularizacion: '/movimientos-inventario/previsualizar_regularizacion/',
  movimientosRegularizar: '/movimientos-inventario/regularizar/',
  movimientosTrasladar: '/movimientos-inventario/trasladar/',
  ajustesMasivos: '/ajustes-masivos/',
  trasladosMasivos: '/traslados-masivos/',
}

async function getList(endpoint, params) {
  const { data } = await api.get(endpoint, { params, suppressGlobalErrorToast: true })
  return normalizeListResponse(data)
}

async function getPaginated(endpoint, params) {
  const { data } = await api.get(endpoint, { params, suppressGlobalErrorToast: true })
  return normalizePaginatedResponse(data)
}

async function getAllPaginated(endpoint, params, { pageSize = 100, maxPages = 50 } = {}) {
  let page = 1
  let next = true
  const rows = []

  while (next && page <= maxPages) {
    const data = await getPaginated(endpoint, {
      ...(params || {}),
      page,
      page_size: pageSize,
    })
    rows.push(...normalizeListResponse(data))
    next = Boolean(data.next)
    page += 1
  }

  return rows
}

async function getOne(endpoint, id) {
  const { data } = await api.get(`${endpoint}${id}/`, { suppressGlobalErrorToast: true })
  return data
}

async function postOne(endpoint, payload) {
  const { data } = await api.post(endpoint, payload, { suppressGlobalErrorToast: true })
  return data
}

async function patchOne(endpoint, id, payload) {
  const { data } = await api.patch(`${endpoint}${id}/`, payload, { suppressGlobalErrorToast: true })
  return data
}

async function executeDetailAction(endpoint, id, action, { method = 'post', payload } = {}) {
  const target = `${endpoint}${id}/${action}/`
  if (method === 'post') {
    const { data } = await api.post(target, payload || {}, { suppressGlobalErrorToast: true })
    return data
  }
  const { data } = await api.get(target, { suppressGlobalErrorToast: true })
  return data
}

async function getMovimientoAuditoria(movimientoId, params) {
  const { data } = await api.get(`${INVENTARIO_ENDPOINTS.movimientos}${movimientoId}/auditoria/`, {
    params,
    suppressGlobalErrorToast: true,
  })
  return normalizePaginatedResponse(data)
}

export const inventarioApi = {
  endpoints: INVENTARIO_ENDPOINTS,
  normalizeListResponse,
  normalizePaginatedResponse,
  getList,
  getPaginated,
  getAllPaginated,
  getOne,
  postOne,
  patchOne,
  executeDetailAction,
  getMovimientoAuditoria,
}
