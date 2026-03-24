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

export const CONTACTOS_ENDPOINTS = {
  contactos: '/contactos/',
  tercerosDetail: '/contactos/',
  clientes: '/clientes/',
  proveedores: '/proveedores/',
  direcciones: '/direcciones/',
  cuentasBancarias: '/contactos/cuentas-bancarias/',
}

async function getList(endpoint, params) {
  const { data } = await api.get(endpoint, { params, suppressGlobalErrorToast: true })
  return normalizeListResponse(data)
}

async function getOne(endpoint, id) {
  const { data } = await api.get(`${endpoint}${id}/`, { suppressGlobalErrorToast: true })
  return data
}

async function getTerceroDetail(contactoId) {
  const { data } = await api.get(`${CONTACTOS_ENDPOINTS.tercerosDetail}${contactoId}/detalle-tercero/`, {
    suppressGlobalErrorToast: true,
  })
  return data
}

async function getTerceroAudit(contactoId, params) {
  const { data } = await api.get(`${CONTACTOS_ENDPOINTS.tercerosDetail}${contactoId}/auditoria/`, {
    params,
    suppressGlobalErrorToast: true,
  })
  return data
}

async function getClienteEditDetail(clienteId) {
  const { data } = await api.get(`${CONTACTOS_ENDPOINTS.clientes}${clienteId}/detalle-edicion/`, {
    suppressGlobalErrorToast: true,
  })
  return data
}

async function getProveedorEditDetail(proveedorId) {
  const { data } = await api.get(`${CONTACTOS_ENDPOINTS.proveedores}${proveedorId}/detalle-edicion/`, {
    suppressGlobalErrorToast: true,
  })
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

async function updateOneWithAction(endpoint, id, action, payload) {
  const { data } = await api.patch(`${endpoint}${id}/${action}/`, payload, { suppressGlobalErrorToast: true })
  return data
}

async function removeOne(endpoint, id) {
  await api.delete(`${endpoint}${id}/`, { suppressGlobalErrorToast: true })
}

export const contactosApi = {
  endpoints: CONTACTOS_ENDPOINTS,
  normalizeListResponse,
  getList,
  getOne,
  getTerceroDetail,
  getTerceroAudit,
  getClienteEditDetail,
  getProveedorEditDetail,
  createOne,
  updateOne,
  updateOneWithAction,
  removeOne,
}
