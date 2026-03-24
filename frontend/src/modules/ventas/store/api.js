import { useCallback, useEffect, useState } from 'react'
import { api } from '@/api/client'
import { VENTAS_ENDPOINTS } from '@/modules/ventas/constants'
import { normalizeListResponse } from '@/modules/ventas/utils'

async function getList(endpoint, params) {
  const { data } = await api.get(endpoint, { params, suppressGlobalErrorToast: true })
  return normalizeListResponse(data)
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

async function executeAction(endpoint, id, action, payload = {}) {
  const { data } = await api.post(`${endpoint}${id}/${action}/`, payload, { suppressGlobalErrorToast: true })
  return data
}

async function resolveProductoPrecio(productoId, params) {
  if (!productoId) {
    return null
  }

  try {
    const { data } = await api.get(`/productos/${productoId}/precio/`, {
      params,
      suppressGlobalErrorToast: true,
    })
    return data
  } catch {
    return null
  }
}

function useListResource(endpoint, params) {
  const [data, setData] = useState([])
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)

  const reload = useCallback(async () => {
    setStatus('loading')
    setError(null)
    try {
      const rows = await getList(endpoint, params)
      setData(rows)
      setStatus('succeeded')
      return rows
    } catch (err) {
      setError(err)
      setStatus('failed')
      throw err
    }
  }, [endpoint, params])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void reload().catch(() => undefined)
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [reload])

  return { data, status, error, reload, setData }
}

export function useListPedidos(params) {
  return useListResource(VENTAS_ENDPOINTS.pedidos, params)
}

export function useListGuias(params) {
  return useListResource(VENTAS_ENDPOINTS.guias, params)
}

export function useListFacturas(params) {
  return useListResource(VENTAS_ENDPOINTS.facturas, params)
}

export function useListNotasCredito(params) {
  return useListResource(VENTAS_ENDPOINTS.notas, params)
}

export const ventasApi = {
  getList,
  getOne,
  createOne,
  updateOne,
  removeOne,
  executeAction,
  resolveProductoPrecio,
  endpoints: VENTAS_ENDPOINTS,
}
