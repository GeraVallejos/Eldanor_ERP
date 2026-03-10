import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function formatMoney(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }

  return Math.round(num).toLocaleString('es-CL')
}

function ComprasOrdenesListPage() {
  const [status, setStatus] = useState('idle')
  const [ordenes, setOrdenes] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [search, setSearch] = useState('')
  const [updatingId, setUpdatingId] = useState(null)

  const loadData = async () => {
    setStatus('loading')
    try {
      const [{ data: ordenesData }, { data: proveedoresData }, { data: contactosData }] = await Promise.all([
        api.get('/ordenes-compra/', { suppressGlobalErrorToast: true }),
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
      ])

      setOrdenes(normalizeListResponse(ordenesData))
      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las ordenes de compra.' }))
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  const proveedorById = useMemo(() => {
    const map = new Map()
    proveedores.forEach((proveedor) => {
      map.set(String(proveedor.id), proveedor)
    })
    return map
  }, [proveedores])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => {
      map.set(String(contacto.id), contacto)
    })
    return map
  }, [contactos])

  const filteredOrdenes = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) {
      return ordenes
    }

    return ordenes.filter((orden) => {
      const proveedor = proveedorById.get(String(orden.proveedor))
      const contacto = contactoById.get(String(proveedor?.contacto))
      const numero = String(orden.numero || '').toLowerCase()
      const estado = String(orden.estado || '').toLowerCase()
      const proveedorNombre = String(contacto?.nombre || '').toLowerCase()
      return numero.includes(query) || estado.includes(query) || proveedorNombre.includes(query)
    })
  }, [ordenes, search, proveedorById, contactoById])

  const updateEstado = async (orden, action) => {
    setUpdatingId(orden.id)
    try {
      const { data } = await api.post(`/ordenes-compra/${orden.id}/${action}/`, {}, { suppressGlobalErrorToast: true })
      setOrdenes((prev) => prev.map((row) => (String(row.id) === String(orden.id) ? { ...row, ...data } : row)))
      toast.success(action === 'enviar' ? 'Orden enviada correctamente.' : 'Orden anulada correctamente.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar la orden.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Ordenes de compra</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <Button variant="outline" size="md" fullWidth className="sm:w-auto" onClick={loadData}>
            Recargar
          </Button>
          <Link
            to="/compras/ordenes/nuevo"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Nueva orden
          </Link>
          <Link
            to="/compras/recepciones"
            className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Recepciones
          </Link>
        </div>
      </div>

      <div className="relative w-full md:max-w-sm">
        <input
          type="text"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar por numero, proveedor o estado..."
          className="w-full rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm"
        />
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando ordenes...</p> : null}

      {status === 'succeeded' ? (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Numero</th>
                <th className="px-3 py-2 text-left font-medium">Proveedor</th>
                <th className="px-3 py-2 text-left font-medium">Fecha emision</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
                <th className="px-3 py-2 text-left font-medium">Total</th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrdenes.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={6}>
                    No hay ordenes de compra.
                  </td>
                </tr>
              ) : (
                filteredOrdenes.map((orden) => {
                  const proveedor = proveedorById.get(String(orden.proveedor))
                  const contacto = contactoById.get(String(proveedor?.contacto))

                  return (
                    <tr key={orden.id} className="border-t border-border">
                      <td className="px-3 py-2">{orden.numero}</td>
                      <td className="px-3 py-2">{contacto?.nombre || '-'}</td>
                      <td className="px-3 py-2">{orden.fecha_emision || '-'}</td>
                      <td className="px-3 py-2">{orden.estado || '-'}</td>
                      <td className="px-3 py-2">{formatMoney(orden.total)}</td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-2">
                          {orden.estado === 'BORRADOR' ? (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updatingId === orden.id}
                              onClick={() => updateEstado(orden, 'enviar')}
                            >
                              Enviar
                            </Button>
                          ) : null}

                          {orden.estado !== 'CANCELADA' && orden.estado !== 'RECIBIDA' ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="border-destructive/40 text-destructive hover:bg-destructive/10"
                              disabled={updatingId === orden.id}
                              onClick={() => updateEstado(orden, 'anular')}
                            >
                              Anular
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}

export default ComprasOrdenesListPage
