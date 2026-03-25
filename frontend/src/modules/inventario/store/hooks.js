import { useCallback, useEffect, useMemo, useState } from 'react'
import { inventarioApi } from '@/modules/inventario/store/api'

const EMPTY_ROWS = []
const EMPTY_PAGINATION = { count: 0, next: null, previous: null }

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

    return inventarioApi.getPaginated(inventarioApi.endpoints.movimientosHistorial, params)
  }, [documentoTipo, stableFilters])

  const reload = useCallback(async (overrides = {}) => {
    if (!enabled) {
      return null
    }

    setStatus('loading')
    setError(null)
    try {
      const response = await loadHistorial(overrides)
      setRows(response.results)
      setPagination({
        count: response.count,
        next: response.next,
        previous: response.previous,
      })
      setStatus('succeeded')
      return response
    } catch (loadError) {
      setRows(EMPTY_ROWS)
      setPagination(EMPTY_PAGINATION)
      setStatus('failed')
      setError(loadError)
      throw loadError
    }
  }, [enabled, loadHistorial])

  useEffect(() => {
    if (!enabled) {
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
        setRows(EMPTY_ROWS)
        setPagination(EMPTY_PAGINATION)
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
    rows: enabled ? rows : EMPTY_ROWS,
    pagination: enabled ? pagination : EMPTY_PAGINATION,
    status: enabled ? status : 'idle',
    error: enabled ? error : null,
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
        results: EMPTY_ROWS,
        count: 0,
        next: null,
        previous: null,
      }
    }
    return inventarioApi.getMovimientoAuditoria(movimientoId, {
      ...(stableParams || {}),
      ...overrides,
    })
  }, [movimientoId, stableParams])

  const reload = useCallback(async (overrides = {}) => {
    if (!enabled || !movimientoId) {
      return null
    }

    setStatus('loading')
    setError(null)
    try {
      const response = await loadAudit(overrides)
      setRows(response.results)
      setPagination({
        count: response.count,
        next: response.next,
        previous: response.previous,
      })
      setStatus('succeeded')
      return response
    } catch (loadError) {
      setRows(EMPTY_ROWS)
      setPagination(EMPTY_PAGINATION)
      setStatus('failed')
      setError(loadError)
      throw loadError
    }
  }, [enabled, loadAudit, movimientoId])

  useEffect(() => {
    if (!enabled || !movimientoId) {
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
        setRows(EMPTY_ROWS)
        setPagination(EMPTY_PAGINATION)
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
    rows: enabled && movimientoId ? rows : EMPTY_ROWS,
    pagination: enabled && movimientoId ? pagination : EMPTY_PAGINATION,
    status: enabled && movimientoId ? status : 'idle',
    error: enabled && movimientoId ? error : null,
    reload,
  }
}

export {
  useInventarioHistorial,
  useMovimientoAuditoria,
}
