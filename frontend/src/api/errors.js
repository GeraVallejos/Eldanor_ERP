import { toast } from 'sonner'

function firstArrayValue(value) {
  return Array.isArray(value) && value.length > 0 ? value[0] : null
}

function toMessage(value) {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed || null
  }

  if (value == null) {
    return null
  }

  const asString = String(value).trim()
  if (asString && asString !== '[object Object]') {
    return asString
  }

  return null
}

export function normalizeApiError(error, options = {}) {
  const {
    fallback = 'Ocurrio un error inesperado.',
    networkFallback = 'No pudimos conectar con el servidor. Intenta nuevamente.',
    transformDetail,
    statusMessages,
  } = options

  const response = error?.response
  const data = response?.data
  const status = response?.status

  const topLevelMessage = toMessage(data)
  if (topLevelMessage) {
    return topLevelMessage
  }

  const topLevelArrayMessage = toMessage(firstArrayValue(data))
  if (topLevelArrayMessage) {
    return topLevelArrayMessage
  }

  const detail = data?.detail
  const detailMessage = toMessage(detail)
  if (detailMessage) {
    const transformed = transformDetail ? transformDetail(detail) : null
    if (typeof transformed === 'string' && transformed.trim()) {
      return transformed
    }
    return detailMessage
  }

  const detailFromArray = toMessage(firstArrayValue(detail))
  if (detailFromArray) {
    return detailFromArray
  }

  const nonFieldError = toMessage(firstArrayValue(data?.non_field_errors))
  if (nonFieldError) {
    return nonFieldError
  }

  if (data && typeof data === 'object') {
    const firstFieldError = Object.values(data)
      .map((value) => (Array.isArray(value) ? value[0] : value))
      .map((value) => toMessage(value))
      .find(Boolean)

    if (firstFieldError) {
      return firstFieldError
    }
  }

  if (!response) {
    return networkFallback
  }

  if (statusMessages && status && typeof statusMessages[status] === 'string') {
    return statusMessages[status]
  }

  return fallback
}

function shouldShowGlobalToast(error) {
  if (!error) {
    return false
  }

  if (error?.code === 'ERR_CANCELED') {
    return false
  }

  if (error?.code === 'ECONNABORTED' || !error?.response) {
    return true
  }

  const status = error.response.status
  return typeof status === 'number' && status >= 500
}

export function notifyGlobalApiError(error, options = {}) {
  const suppressGlobalErrorToast =
    options?.suppressGlobalErrorToast ?? error?.config?.suppressGlobalErrorToast

  if (suppressGlobalErrorToast) {
    return
  }

  if (!shouldShowGlobalToast(error)) {
    return
  }

  toast.error(normalizeApiError(error, options))
}
