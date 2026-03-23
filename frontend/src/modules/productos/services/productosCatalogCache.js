import { api } from '@/api/client'

const DEFAULT_TTL_MS = 15000

const cacheState = {
  lookupCache: new Map(),
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
  cacheState.lookupCache.clear()
}

function buildLookupCacheKey({ query = '', tipo = '', limit = 50 }) {
  return JSON.stringify({
    query: String(query || '').trim().toLowerCase(),
    tipo: String(tipo || '').trim().toUpperCase(),
    limit: Number(limit || 50),
  })
}

export async function searchProductosCatalog({ query = '', tipo = '', limit = 50, forceRefresh = false, ttlMs = DEFAULT_TTL_MS } = {}) {
  const normalizedQuery = String(query || '').trim()
  const normalizedTipo = String(tipo || '').trim().toUpperCase()
  const normalizedLimit = Math.max(1, Number(limit || 50))
  const cacheKey = buildLookupCacheKey({ query: normalizedQuery, tipo: normalizedTipo, limit: normalizedLimit })
  const now = Date.now()
  const cached = cacheState.lookupCache.get(cacheKey)

  if (!forceRefresh && cached?.data && cached.expiresAt > now) {
    return cached.data
  }

  if (!forceRefresh && cached?.pendingPromise) {
    return cached.pendingPromise
  }

  const params = {}
  if (normalizedQuery) {
    params.q = normalizedQuery
  }
  if (normalizedTipo) {
    params.tipo = normalizedTipo
  }
  params.limit = normalizedLimit

  const pendingPromise = api
    .get('/productos/', { params, suppressGlobalErrorToast: true })
    .then(({ data }) => normalizeListResponse(data).slice(0, normalizedLimit))
    .then((normalized) => {
      cacheState.lookupCache.set(cacheKey, {
        data: normalized,
        expiresAt: Date.now() + ttlMs,
        pendingPromise: null,
      })
      return normalized
    })
    .finally(() => {
      const current = cacheState.lookupCache.get(cacheKey)
      if (current) {
        cacheState.lookupCache.set(cacheKey, { ...current, pendingPromise: null })
      }
    })

  cacheState.lookupCache.set(cacheKey, {
    data: cached?.data || null,
    expiresAt: cached?.expiresAt || 0,
    pendingPromise,
  })

  return pendingPromise
}

export function mergeProductosCatalog(current, incoming) {
  const byId = new Map()
  ;[...(Array.isArray(current) ? current : []), ...(Array.isArray(incoming) ? incoming : [])].forEach((producto) => {
    if (!producto?.id) {
      return
    }
    byId.set(String(producto.id), producto)
  })
  return Array.from(byId.values())
}
