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
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)

  const reload = useCallback(async () => {
    setStatus('loading')
    setError(null)

    const params = includeInactive ? { include_inactive: '1' } : undefined

    try {
      const endpoint = contactosApi.endpoints[resource]
      const resourceRows = await contactosApi.getList(endpoint, params)

      setRows(sortByCreatedDesc(resourceRows))
      setStatus('succeeded')
      return { rows: resourceRows }
    } catch (loadError) {
      setRows([])
      setStatus('failed')
      setError(loadError)
      throw loadError
    }
  }, [includeInactive, resource])

  useEffect(() => {
    void reload()
  }, [reload])

  return {
    rows,
    status,
    error,
    reload,
  }
}

function useTerceroDetail(contactoId) {
  const [status, setStatus] = useState('idle')
  const [contacto, setContacto] = useState(null)
  const [cliente, setCliente] = useState(null)
  const [proveedor, setProveedor] = useState(null)
  const [direcciones, setDirecciones] = useState([])
  const [cuentasBancarias, setCuentasBancarias] = useState([])

  const reload = useCallback(async () => {
    if (!contactoId) {
      return null
    }

    setStatus('loading')

    try {
      const terceroDetail = await contactosApi.getTerceroDetail(contactoId)

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
  }, [contactoId])

  useEffect(() => {
    void reload()
  }, [reload])

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
