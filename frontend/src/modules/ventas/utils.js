import { formatCurrencyCLP } from '@/lib/numberFormat'
export { hasPermission } from '@/modules/shared/auth/permissions'

export function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export function formatEstadoLabel(value) {
  const raw = String(value || '').trim()
  if (!raw) return '-'
  return raw.replaceAll('_', ' ')
}

export function formatMoney(value) {
  return formatCurrencyCLP(value)
}

export function buildErrorMessage(error) {
  const detail = error?.response?.data?.detail
  const errorCode = error?.response?.data?.error_code
  if (typeof detail === 'string' && detail.trim()) {
    return errorCode ? `${detail} (${errorCode})` : detail
  }
  if (Array.isArray(detail) && detail[0]) {
    return String(detail[0])
  }
  if (detail && typeof detail === 'object') {
    const first = Object.values(detail).find((v) => Array.isArray(v) ? v[0] : v)
    if (first) return Array.isArray(first) ? String(first[0]) : String(first)
  }
  return 'No se pudo procesar la solicitud.'
}
