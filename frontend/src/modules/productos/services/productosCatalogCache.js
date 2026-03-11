import { api } from '@/api/client'

const DEFAULT_TTL_MS = 15000

const cacheState = {
  data: null,
  expiresAt: 0,
  pendingPromise: null,
}

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

export function invalidateProductosCatalogCache() {
  cacheState.data = null
  cacheState.expiresAt = 0
  cacheState.pendingPromise = null
}

export async function getProductosCatalog({ forceRefresh = false, ttlMs = DEFAULT_TTL_MS } = {}) {
  const now = Date.now()

  if (!forceRefresh && cacheState.data && cacheState.expiresAt > now) {
    return cacheState.data
  }

  if (!forceRefresh && cacheState.pendingPromise) {
    return cacheState.pendingPromise
  }

  cacheState.pendingPromise = api
    .get('/productos/', { suppressGlobalErrorToast: true })
    .then(({ data }) => {
      const normalized = normalizeListResponse(data)
      cacheState.data = normalized
      cacheState.expiresAt = Date.now() + ttlMs
      return normalized
    })
    .finally(() => {
      cacheState.pendingPromise = null
    })

  return cacheState.pendingPromise
}
