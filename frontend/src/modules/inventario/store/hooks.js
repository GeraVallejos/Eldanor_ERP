import { useCallback, useEffect, useMemo, useState } from 'react'
import { inventarioApi } from '@/modules/inventario/store/api'

function buildStableObjectKey(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return JSON.stringify(value ?? null)
  }

  const sorted = Object.keys(value)
    .sort()
    .reduce((acc, key) => {
      acc[key] = value[key]
      return acc
    }, {})

  return JSON.stringify(sorted)
}

function useInventarioHistorial({
  documentoTipo = '',
  filters = {},
  enabled = true,
} = {}) {
  const [rows, setRows] = useState([])
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null })
  const [status, setStatus] = useState(enabled ? 'loading' : 'idle')
  const [error, setError] = useState(null)
  const filtersKey = buildStableObjectKey(filters)
  const stableFilters = useMemo(() => JSON.parse(filtersKey), [filtersKey])

  const loadHistorial = useCallback(async (overrides = {}) => {
    const params = {
      ...stableFilters,
      ...overrides,
    }
    if (documentoTipo) {
      params.documento_tipo = documentoTipo
    }

    const response = await inventarioApi.getPaginated(inventarioApi.endpoints.movimientosHistorial, params)
    setRows(response.results)
    setPagination({
      count: response.count,
      next: response.next,
      previous: response.previous,
    })
    return response
  }, [documentoTipo, stableFilters])

  const reload = useCallback(async (overrides = {}) => {
    if (!enabled) {
      setRows([])
      setPagination({ count: 0, next: null, previous: null })
      setStatus('idle')
      return null
    }

    setStatus('loading')
    setError(null)
    try {
      const response = await loadHistorial(overrides)
      setStatus('succeeded')
      return response
    } catch (loadError) {
      setRows([])
      setPagination({ count: 0, next: null, previous: null })
      setStatus('failed')
      setError(loadError)
      throw loadError
    }
  }, [enabled, loadHistorial])

  useEffect(() => {
    if (!enabled) {
      setRows([])
      setPagination({ count: 0, next: null, previous: null })
      setStatus('idle')
      return
    }

    let active = true

    const bootstrap = async () => {
      setStatus('loading')
      setError(null)
      try {
        const response = await loadHistorial()
        if (!active) {
          return
        }
        setRows(response.results)
        setPagination({
          count: response.count,
          next: response.next,
          previous: response.previous,
        })
        setStatus('succeeded')
      } catch (loadError) {
        if (!active) {
          return
        }
        setRows([])
        setPagination({ count: 0, next: null, previous: null })
        setStatus('failed')
        setError(loadError)
      }
    }

    void bootstrap()

    return () => {
      active = false
    }
  }, [enabled, loadHistorial])

  return {
    rows,
    pagination,
    status,
    error,
    reload,
  }
}

function useMovimientoAuditoria(movimientoId, { enabled = true, params } = {}) {
  const [rows, setRows] = useState([])
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null })
  const [status, setStatus] = useState(enabled && movimientoId ? 'loading' : 'idle')
  const [error, setError] = useState(null)
  const paramsKey = buildStableObjectKey(params)
  const stableParams = useMemo(() => JSON.parse(paramsKey), [paramsKey])

  const loadAudit = useCallback(async (overrides = {}) => {
    if (!movimientoId) {
      return {
        results: [],
        count: 0,
        next: null,
        previous: null,
      }
    }
    const response = await inventarioApi.getMovimientoAuditoria(movimientoId, {
      ...(stableParams || {}),
      ...overrides,
    })
    setRows(response.results)
    setPagination({
      count: response.count,
      next: response.next,
      previous: response.previous,
    })
    return response
  }, [movimientoId, stableParams])

  const reload = useCallback(async (overrides = {}) => {
    if (!enabled || !movimientoId) {
      setRows([])
      setPagination({ count: 0, next: null, previous: null })
      setStatus('idle')
      return null
    }

    setStatus('loading')
    setError(null)
    try {
      const response = await loadAudit(overrides)
      setStatus('succeeded')
      return response
    } catch (loadError) {
      setRows([])
      setPagination({ count: 0, next: null, previous: null })
      setStatus('failed')
      setError(loadError)
      throw loadError
    }
  }, [enabled, loadAudit, movimientoId])

  useEffect(() => {
    if (!enabled || !movimientoId) {
      setRows([])
      setPagination({ count: 0, next: null, previous: null })
      setStatus('idle')
      return
    }

    let active = true

    const bootstrap = async () => {
      setStatus('loading')
      setError(null)
      try {
        const response = await loadAudit()
        if (!active) {
          return
        }
        setRows(response.results)
        setPagination({
          count: response.count,
          next: response.next,
          previous: response.previous,
        })
        setStatus('succeeded')
      } catch (loadError) {
        if (!active) {
          return
        }
        setRows([])
        setPagination({ count: 0, next: null, previous: null })
        setStatus('failed')
        setError(loadError)
      }
    }

    void bootstrap()

    return () => {
      active = false
    }
  }, [enabled, loadAudit, movimientoId])

  return {
    rows,
    pagination,
    status,
    error,
    reload,
  }
}

export {
  useInventarioHistorial,
  useMovimientoAuditoria,
}
