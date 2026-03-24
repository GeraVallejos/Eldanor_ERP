import { useCallback, useEffect, useState } from 'react'
import { contactosApi } from '@/modules/contactos/store/api'

function sortByCreatedDesc(items) {
  return [...items].sort((left, right) => {
    return String(right?.creado_en || '').localeCompare(String(left?.creado_en || ''))
  })
}

function useContactosListado({
  resource = 'clientes',
  includeInactive = false,
} = {}) {
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)

  const loadRows = useCallback(async () => {
    const params = includeInactive ? { include_inactive: '1' } : undefined
    const endpoint = contactosApi.endpoints[resource]
    return contactosApi.getList(endpoint, params)
  }, [includeInactive, resource])

  const reload = useCallback(async () => {
    setStatus('loading')
    setError(null)

    try {
      const resourceRows = await loadRows()

      setRows(sortByCreatedDesc(resourceRows))
      setStatus('succeeded')
      return { rows: resourceRows }
    } catch (loadError) {
      setRows([])
      setStatus('failed')
      setError(loadError)
      throw loadError
    }
  }, [loadRows])

  useEffect(() => {
    let active = true

    const bootstrapRows = async () => {
      try {
        const resourceRows = await loadRows()
        if (!active) {
          return
        }
        setRows(sortByCreatedDesc(resourceRows))
        setStatus('succeeded')
        setError(null)
      } catch (loadError) {
        if (!active) {
          return
        }
        setRows([])
        setStatus('failed')
        setError(loadError)
      }
    }

    void bootstrapRows()

    return () => {
      active = false
    }
  }, [loadRows])

  return {
    rows,
    status,
    error,
    reload,
  }
}

function useTerceroDetail(contactoId) {
  const [status, setStatus] = useState(contactoId ? 'loading' : 'idle')
  const [contacto, setContacto] = useState(null)
  const [cliente, setCliente] = useState(null)
  const [proveedor, setProveedor] = useState(null)
  const [direcciones, setDirecciones] = useState([])
  const [cuentasBancarias, setCuentasBancarias] = useState([])

  const loadTerceroDetail = useCallback(async () => {
    if (!contactoId) {
      return null
    }

    return contactosApi.getTerceroDetail(contactoId)
  }, [contactoId])

  const reload = useCallback(async () => {
    if (!contactoId) {
      return null
    }

    setStatus('loading')

    try {
      const terceroDetail = await loadTerceroDetail()

      setContacto({
        id: terceroDetail.id,
        nombre: terceroDetail.nombre,
        razon_social: terceroDetail.razon_social,
        rut: terceroDetail.rut,
        tipo: terceroDetail.tipo,
        email: terceroDetail.email,
        telefono: terceroDetail.telefono,
        celular: terceroDetail.celular,
        activo: terceroDetail.activo,
        notas: terceroDetail.notas,
      })
      setCliente(terceroDetail.cliente || null)
      setProveedor(terceroDetail.proveedor || null)
      setDirecciones(terceroDetail.direcciones || [])
      setCuentasBancarias(terceroDetail.cuentas_bancarias || [])
      setStatus('succeeded')

      return {
        contacto: {
          id: terceroDetail.id,
          nombre: terceroDetail.nombre,
          razon_social: terceroDetail.razon_social,
          rut: terceroDetail.rut,
          tipo: terceroDetail.tipo,
          email: terceroDetail.email,
          telefono: terceroDetail.telefono,
          celular: terceroDetail.celular,
          activo: terceroDetail.activo,
          notas: terceroDetail.notas,
        },
        cliente: terceroDetail.cliente || null,
        proveedor: terceroDetail.proveedor || null,
        direcciones: terceroDetail.direcciones || [],
        cuentasBancarias: terceroDetail.cuentas_bancarias || [],
      }
    } catch (error) {
      setStatus('failed')
      throw error
    }
  }, [contactoId, loadTerceroDetail])

  useEffect(() => {
    if (!contactoId) {
      return
    }

    let active = true

    const bootstrapDetail = async () => {
      try {
        const terceroDetail = await loadTerceroDetail()
        if (!active || !terceroDetail) {
          return
        }

        setContacto({
          id: terceroDetail.id,
          nombre: terceroDetail.nombre,
          razon_social: terceroDetail.razon_social,
          rut: terceroDetail.rut,
          tipo: terceroDetail.tipo,
          email: terceroDetail.email,
          telefono: terceroDetail.telefono,
          celular: terceroDetail.celular,
          activo: terceroDetail.activo,
          notas: terceroDetail.notas,
        })
        setCliente(terceroDetail.cliente || null)
        setProveedor(terceroDetail.proveedor || null)
        setDirecciones(terceroDetail.direcciones || [])
        setCuentasBancarias(terceroDetail.cuentas_bancarias || [])
        setStatus('succeeded')
      } catch {
        if (!active) {
          return
        }
        setStatus('failed')
      }
    }

    void bootstrapDetail()

    return () => {
      active = false
    }
  }, [contactoId, loadTerceroDetail])

  return {
    status,
    contacto,
    cliente,
    proveedor,
    direcciones,
    cuentasBancarias,
    reload,
  }
}

export {
  useContactosListado,
  useTerceroDetail,
}
