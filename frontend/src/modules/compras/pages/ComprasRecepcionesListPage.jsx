import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import TablePagination from '@/components/ui/TablePagination'
import { useTableSorting } from '@/lib/tableSorting'
import { cn } from '@/lib/utils'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

const ESTADO_LABELS = {
  BORRADOR: 'Borrador',
  CONFIRMADA: 'Confirmada',
}

const ESTADO_BADGE = {
  BORRADOR: 'bg-yellow-100 text-yellow-800',
  CONFIRMADA: 'bg-green-100 text-green-800',
}

function ComprasRecepcionesListPage() {
  const [status, setStatus] = useState('idle')
  const [recepciones, setRecepciones] = useState([])
  const [ordenes, setOrdenes] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [search, setSearch] = useState('')
  const [estadoFilter, setEstadoFilter] = useState('ALL')
  const [confirmDialog, setConfirmDialog] = useState(null)
  const [confirmBodega, setConfirmBodega] = useState('')
  const [confirmando, setConfirmando] = useState(false)

  const loadData = async () => {
    setStatus('loading')
    try {
      const [
        { data: recepcionesData },
        { data: ordenesData },
        { data: proveedoresData },
        { data: contactosData },
        { data: bodegasData },
      ] = await Promise.all([
        api.get('/recepciones-compra/', { suppressGlobalErrorToast: true }),
        api.get('/ordenes-compra/', { suppressGlobalErrorToast: true }),
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])

      setRecepciones(normalizeListResponse(recepcionesData))
      setOrdenes(normalizeListResponse(ordenesData))
      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setBodegas(normalizeListResponse(bodegasData))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las recepciones.' }))
    }
  }

  useEffect(() => {
    const id = setTimeout(() => { void loadData() }, 0)
    return () => clearTimeout(id)
  }, [])

  const ordenById = useMemo(() => {
    const map = new Map()
    ordenes.forEach((o) => map.set(String(o.id), o))
    return map
  }, [ordenes])

  const proveedorById = useMemo(() => {
    const map = new Map()
    proveedores.forEach((p) => map.set(String(p.id), p))
    return map
  }, [proveedores])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((c) => map.set(String(c.id), c))
    return map
  }, [contactos])

  const filteredRecepciones = useMemo(() => {
    const query = search.trim().toLowerCase()
    return recepciones.filter((rec) => {
      if (estadoFilter !== 'ALL' && rec.estado !== estadoFilter) return false
      if (!query) return true
      const orden = rec.orden_compra ? ordenById.get(String(rec.orden_compra)) : null
      const proveedor = orden ? proveedorById.get(String(orden.proveedor)) : null
      const contacto = proveedor ? contactoById.get(String(proveedor.contacto)) : null
      const numero = String(orden?.numero || '').toLowerCase()
      const provNombre = String(contacto?.nombre || '').toLowerCase()
      const fecha = String(rec.fecha || '').toLowerCase()
      return numero.includes(query) || provNombre.includes(query) || fecha.includes(query)
    })
  }, [recepciones, search, estadoFilter, ordenById, proveedorById, contactoById])

  const { paginatedRows, toggleSort, getSortIndicator, currentPage, totalPages, totalRows, pageSize, nextPage, prevPage } =
    useTableSorting(filteredRecepciones, {
      accessors: {
        fecha: (r) => r.fecha,
        estado: (r) => r.estado,
      },
      pageSize: 10,
      initialKey: 'fecha',
      initialDirection: 'desc',
    })

  const openConfirmDialog = (recepcion) => {
    setConfirmDialog(recepcion)
    setConfirmBodega('')
  }

  const closeConfirmDialog = () => {
    setConfirmDialog(null)
    setConfirmBodega('')
  }

  const handleConfirmar = async () => {
    if (!confirmDialog) return
    setConfirmando(true)
    try {
      const payload = confirmBodega ? { bodega_id: confirmBodega } : {}
      const { data } = await api.post(
        `/recepciones-compra/${confirmDialog.id}/confirmar/`,
        payload,
        { suppressGlobalErrorToast: true },
      )
      setRecepciones((prev) => prev.map((r) => (String(r.id) === String(confirmDialog.id) ? { ...r, ...data } : r)))
      toast.success('Recepcion confirmada. El inventario fue actualizado.')
      closeConfirmDialog()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo confirmar la recepcion.' }))
    } finally {
      setConfirmando(false)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Recepciones de compra</h2>
        <Link
          to="/compras/recepciones/nuevo"
          className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
        >
          Nueva recepcion
        </Link>
      </div>

      <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-end">
        <div className="relative w-full sm:max-w-sm">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por OC, proveedor o fecha..."
            className="w-full rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm"
          />
        </div>
        <label className="w-full text-sm sm:max-w-xs">
          Estado
          <select
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
          >
            <option value="ALL">Todas</option>
            <option value="BORRADOR">Borrador</option>
            <option value="CONFIRMADA">Confirmada</option>
          </select>
        </label>
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando recepciones...</p> : null}

      {status === 'succeeded' ? (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('fecha')} className="inline-flex items-center gap-1 hover:text-primary">
                    Fecha <span className="text-xs text-muted-foreground">{getSortIndicator('fecha')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">Orden de compra</th>
                <th className="px-3 py-2 text-left font-medium">Proveedor</th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('estado')} className="inline-flex items-center gap-1 hover:text-primary">
                    Estado <span className="text-xs text-muted-foreground">{getSortIndicator('estado')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">Observaciones</th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecepciones.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={6}>
                    No hay recepciones de compra.
                  </td>
                </tr>
              ) : (
                paginatedRows.map((rec) => {
                  const orden = rec.orden_compra ? ordenById.get(String(rec.orden_compra)) : null
                  const proveedor = orden ? proveedorById.get(String(orden.proveedor)) : null
                  const contacto = proveedor ? contactoById.get(String(proveedor.contacto)) : null

                  return (
                    <tr key={rec.id} className="border-t border-border">
                      <td className="px-3 py-2">{rec.fecha || '-'}</td>
                      <td className="px-3 py-2">
                        {orden ? (
                          <Link to={`/compras/ordenes/${orden.id}`} className="text-primary hover:underline">
                            {orden.numero}
                          </Link>
                        ) : (
                          <span className="text-muted-foreground">Sin OC</span>
                        )}
                      </td>
                      <td className="px-3 py-2">{contacto?.nombre || '-'}</td>
                      <td className="px-3 py-2">
                        <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', ESTADO_BADGE[rec.estado] || 'bg-muted text-muted-foreground')}>
                          {ESTADO_LABELS[rec.estado] || rec.estado}
                        </span>
                      </td>
                      <td className="px-3 py-2 max-w-50 truncate text-muted-foreground">{rec.observaciones || '-'}</td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-2">
                          {rec.estado === 'BORRADOR' ? (
                            <>
                              <Link
                                to={`/compras/recepciones/${rec.id}/editar`}
                                className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-8 px-3 text-xs')}
                              >
                                Editar
                              </Link>
                              <Button
                                size="sm"
                                variant="default"
                                className="h-8 px-3 text-xs"
                                onClick={() => openConfirmDialog(rec)}
                              >
                                Confirmar
                              </Button>
                            </>
                          ) : (
                            <Link
                              to={`/compras/recepciones/${rec.id}/editar`}
                              className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-8 px-3 text-xs')}
                            >
                              Ver
                            </Link>
                          )}
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

      <TablePagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalRows={totalRows}
        pageSize={pageSize}
        onPrev={prevPage}
        onNext={nextPage}
      />

      {/* Dialogo de confirmacion */}
      {confirmDialog ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-background p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold">Confirmar recepcion</h3>
            <p className="text-sm text-muted-foreground">
              Esta accion registrara los movimientos de inventario. No se puede deshacer.
            </p>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Bodega destino (opcional)</label>
              <select
                value={confirmBodega}
                onChange={(e) => setConfirmBodega(e.target.value)}
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Bodega por defecto</option>
                {bodegas.map((b) => (
                  <option key={b.id} value={b.id}>{b.nombre}</option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="md" onClick={closeConfirmDialog} disabled={confirmando}>
                Cancelar
              </Button>
              <Button variant="default" size="md" onClick={handleConfirmar} disabled={confirmando}>
                {confirmando ? 'Confirmando...' : 'Confirmar recepcion'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default ComprasRecepcionesListPage
