import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import DocumentActionsDialog from '@/components/ui/DocumentActionsDialog'
import { buttonVariants } from '@/components/ui/buttonVariants'
import TablePagination from '@/components/ui/TablePagination'
import { useTableSorting } from '@/lib/tableSorting'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

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
  const navigate = useNavigate()
  const [status, setStatus] = useState('idle')
  const [ordenes, setOrdenes] = useState([])
  const [documentos, setDocumentos] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [search, setSearch] = useState('')
  const [estadoFilter, setEstadoFilter] = useState('ACTIVAS')
  const [updatingId, setUpdatingId] = useState(null)
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionType, setActionType] = useState(null)
  const [actionItem, setActionItem] = useState(null)
  const [actionReason, setActionReason] = useState('')

  const loadData = async () => {
    setStatus('loading')
    try {
      const [{ data: ordenesData }, { data: documentosData }, { data: proveedoresData }, { data: contactosData }] = await Promise.all([
        api.get('/ordenes-compra/', { suppressGlobalErrorToast: true }),
        api.get('/documentos-compra/', { suppressGlobalErrorToast: true }),
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
      ])

      setOrdenes(normalizeListResponse(ordenesData))
      setDocumentos(normalizeListResponse(documentosData))
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

  const ultimoDocumentoByOrdenId = useMemo(() => {
    const map = new Map()
    documentos.forEach((doc) => {
      if (!doc?.orden_compra) {
        return
      }

      const key = String(doc.orden_compra)
      const prev = map.get(key)
      if (!prev) {
        map.set(key, doc)
        return
      }

      const prevTs = Date.parse(prev?.creado_en || '') || 0
      const docTs = Date.parse(doc?.creado_en || '') || 0
      if (docTs >= prevTs) {
        map.set(key, doc)
      }
    })

    return map
  }, [documentos])

  const filteredOrdenes = useMemo(() => {
    const query = search.trim().toLowerCase()

    return ordenes.filter((orden) => {
      if (estadoFilter === 'ACTIVAS' && orden.estado === 'CANCELADA') {
        return false
      }

      if (estadoFilter !== 'ACTIVAS' && estadoFilter !== 'ALL' && orden.estado !== estadoFilter) {
        return false
      }

      if (!query) {
        return true
      }

      const proveedor = proveedorById.get(String(orden.proveedor))
      const contacto = contactoById.get(String(proveedor?.contacto))
      const numero = String(orden.numero || '').toLowerCase()
      const estado = String(orden.estado || '').toLowerCase()
      const proveedorNombre = String(contacto?.nombre || '').toLowerCase()
      return numero.includes(query) || estado.includes(query) || proveedorNombre.includes(query)
    })
  }, [ordenes, search, proveedorById, contactoById, estadoFilter])

  const { paginatedRows: paginatedOrdenes, toggleSort, getSortIndicator, currentPage, totalPages, totalRows, pageSize, nextPage, prevPage } = useTableSorting(filteredOrdenes, {
    accessors: {
      creado_en: (orden) => orden.creado_en,
      numero: (orden) => orden.numero,
      proveedor: (orden) => {
        const proveedor = proveedorById.get(String(orden.proveedor))
        const contacto = contactoById.get(String(proveedor?.contacto))
        return contacto?.nombre || ''
      },
      fecha_emision: (orden) => orden.fecha_emision,
      estado: (orden) => orden.estado,
      total: (orden) => Number(orden.total || 0),
    },
    pageSize: 10,
    initialKey: 'creado_en',
    initialDirection: 'desc',
  })

  const updateEstado = async (orden, action) => {
    setUpdatingId(orden.id)
    try {
      const { data } = await api.post(`/ordenes-compra/${orden.id}/${action}/`, {}, { suppressGlobalErrorToast: true })
      setOrdenes((prev) => prev.map((row) => (String(row.id) === String(orden.id) ? { ...row, ...data } : row)))
      toast.success('Orden anulada correctamente.')
    } catch (error) {
      const fallback =
        action === 'anular'
          ? 'No se puede anular la orden. Verifique si tiene documentos de compra activos asociados.'
          : 'No se pudo actualizar la orden.'
      toast.error(normalizeApiError(error, { fallback }))
    } finally {
      setUpdatingId(null)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!actionItem || actionType !== 'eliminar') return

    setUpdatingId(actionItem.id)
    try {
      await api.post(`/ordenes-compra/${actionItem.id}/eliminar_sin_documentos/`, {}, { suppressGlobalErrorToast: true })
      setOrdenes((prev) => prev.filter((row) => String(row.id) !== String(actionItem.id)))
      toast.success('Orden eliminada correctamente.')
      closeActionDialog()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar la orden.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  const openActionDialog = (orden, action) => {
    setActionItem(orden)
    setActionType(action)
    setActionReason('')
    setActionDialogOpen(true)
  }

  const closeActionDialog = () => {
    setActionDialogOpen(false)
    setActionItem(null)
    setActionType(null)
    setActionReason('')
  }

  const handleActionConfirm = async () => {
    if (!actionItem || !actionType) return

    if (actionType === 'eliminar') {
      await handleDeleteConfirm()
      return
    }

    setUpdatingId(actionItem.id)
    try {
      if (actionType === 'corregir') {
        const response = await api.post(
          `/ordenes-compra/${actionItem.id}/corregir/`,
          { motivo: actionReason.trim() },
          { suppressGlobalErrorToast: true },
        )
        setOrdenes((prev) => [...prev, response.data])
        toast.success('Orden corregida. Se creó un nuevo borrador.')
        closeActionDialog()
      } else if (actionType === 'duplicar') {
        const [{ data: ordenData }, { data: itemsData }] = await Promise.all([
          api.get(`/ordenes-compra/${actionItem.id}/`, { suppressGlobalErrorToast: true }),
          api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true }),
        ])

        const scopedItems = normalizeListResponse(itemsData).filter(
          (row) => String(row.orden_compra) === String(actionItem.id),
        )

        closeActionDialog()
        navigate('/compras/ordenes/nuevo', {
          state: {
            precargarDe: {
              proveedor: String(ordenData.proveedor || ''),
              fecha_emision: new Date().toISOString().slice(0, 10),
              fecha_entrega: ordenData.fecha_entrega || '',
              observaciones: ordenData.observaciones || '',
              items: scopedItems.map((item) => ({
                producto: String(item.producto || ''),
                descripcion: item.descripcion || '',
                cantidad: String(item.cantidad || '1'),
                precio_unitario: String(item.precio_unitario || '0'),
                impuesto: item.impuesto ? String(item.impuesto) : '',
              })),
            },
          },
        })
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo completar la acción.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  const getTodaySuffix = () => new Date().toISOString().slice(0, 10)

  const handleExportExcel = async () => {
    if (filteredOrdenes.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'OrdenesCompra',
      fileName: `ordenes_compra_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: 'Numero', key: 'numero', width: 18 },
        { header: 'Proveedor', key: 'proveedor', width: 32 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 18 },
        { header: 'Estado', key: 'estado', width: 16 },
        { header: 'Total', key: 'total', width: 16 },
      ],
      rows: filteredOrdenes.map((orden) => {
        const proveedor = proveedorById.get(String(orden.proveedor))
        const contacto = contactoById.get(String(proveedor?.contacto))
        return {
          numero: orden.numero || '-',
          proveedor: contacto?.nombre || '-',
          fecha_emision: orden.fecha_emision || '-',
          estado: orden.estado || '-',
          total: Number(orden.total || 0),
        }
      }),
    })
  }

  const handleExportPdf = async () => {
    if (filteredOrdenes.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Ordenes de compra',
      fileName: `ordenes_compra_${getTodaySuffix()}.pdf`,
      headers: ['Numero', 'Proveedor', 'Fecha emision', 'Estado', 'Total'],
      rows: filteredOrdenes.map((orden) => {
        const proveedor = proveedorById.get(String(orden.proveedor))
        const contacto = contactoById.get(String(proveedor?.contacto))
        return [
          orden.numero || '-',
          contacto?.nombre || '-',
          orden.fecha_emision || '-',
          orden.estado || '-',
          formatMoney(orden.total),
        ]
      }),
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Ordenes de compra</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <Button
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onClick={handleExportExcel}
            disabled={filteredOrdenes.length === 0}
          >
            Exportar Excel
          </Button>
          <Button
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onClick={handleExportPdf}
            disabled={filteredOrdenes.length === 0}
          >
            Exportar PDF
          </Button>
          <Link
            to="/compras/ordenes/nuevo"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Nueva orden
          </Link>
        </div>
      </div>

      <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-end">
        <div className="relative w-full sm:max-w-sm">
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por numero, proveedor o estado..."
            className="w-full rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm"
          />
        </div>

        <label className="w-full text-sm sm:max-w-xs">
          Estado
          <select
            value={estadoFilter}
            onChange={(event) => setEstadoFilter(event.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
          >
            <option value="ACTIVAS">Activas</option>
            <option value="ALL">Todas</option>
            <option value="BORRADOR">Borrador</option>
            <option value="ENVIADA">Enviada</option>
            <option value="PARCIAL">Parcial</option>
            <option value="RECIBIDA">Recibida</option>
            <option value="CANCELADA">Cancelada</option>
          </select>
        </label>
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando ordenes...</p> : null}

      {status === 'succeeded' ? (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('numero')} className="inline-flex items-center gap-1 hover:text-primary">
                    Numero <span className="text-xs text-muted-foreground">{getSortIndicator('numero')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('proveedor')} className="inline-flex items-center gap-1 hover:text-primary">
                    Proveedor <span className="text-xs text-muted-foreground">{getSortIndicator('proveedor')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('fecha_emision')} className="inline-flex items-center gap-1 hover:text-primary">
                    Fecha emision <span className="text-xs text-muted-foreground">{getSortIndicator('fecha_emision')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('estado')} className="inline-flex items-center gap-1 hover:text-primary">
                    Estado <span className="text-xs text-muted-foreground">{getSortIndicator('estado')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('total')} className="inline-flex items-center gap-1 hover:text-primary">
                    Total <span className="text-xs text-muted-foreground">{getSortIndicator('total')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">Documentos asociados</th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrdenes.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={7}>
                    No hay ordenes de compra.
                  </td>
                </tr>
              ) : (
                paginatedOrdenes.map((orden) => {
                  const proveedor = proveedorById.get(String(orden.proveedor))
                  const contacto = contactoById.get(String(proveedor?.contacto))
                  const ultimoDocAsociado = ultimoDocumentoByOrdenId.get(String(orden.id))

                  return (
                    <tr key={orden.id} className="border-t border-border">
                      <td className="px-3 py-2">{orden.numero}</td>
                      <td className="px-3 py-2">{contacto?.nombre || '-'}</td>
                      <td className="px-3 py-2">{orden.fecha_emision || '-'}</td>
                      <td className="px-3 py-2">{orden.estado || '-'}</td>
                      <td className="px-3 py-2">{formatMoney(orden.total)}</td>
                      <td className="px-3 py-2">
                        {!ultimoDocAsociado ? (
                          <span className="text-muted-foreground">-</span>
                        ) : (
                          <Link
                            to={`/compras/documentos/${ultimoDocAsociado.id}`}
                            className="text-xs text-primary hover:underline"
                          >
                            {ultimoDocAsociado.tipo_documento === 'FACTURA_COMPRA' ? 'FAC' : 'GUIA'}
                            {' '}
                            {ultimoDocAsociado.serie ? `${ultimoDocAsociado.serie}-` : ''}
                            {ultimoDocAsociado.folio || 'S/F'}
                            {' '}
                            ({ultimoDocAsociado.estado || '-'})
                          </Link>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-2">
                          <Link
                            to={`/compras/ordenes/${orden.id}`}
                            className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-8 px-3 text-xs')}
                          >
                            Ver
                          </Link>

                          {orden.estado === 'BORRADOR' ? (
                            <Link
                              to={`/compras/documentos/nuevo?orden_compra=${orden.id}`}
                              className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-8 px-3 text-xs')}
                            >
                              Crear doc
                            </Link>
                          ) : null}

                          {orden.estado === 'BORRADOR' ? (
                            <Link
                              to={`/compras/ordenes/${orden.id}/editar`}
                              className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-8 px-3 text-xs')}
                            >
                              Editar
                            </Link>
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

                          {orden.estado !== 'BORRADOR' && orden.estado !== 'CANCELADA' && !orden.tiene_documentos_activos ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-xs"
                              disabled={updatingId === orden.id}
                              onClick={() => openActionDialog(orden, 'corregir')}
                            >
                              Corregir
                            </Button>
                          ) : null}

                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs"
                            disabled={updatingId === orden.id}
                            onClick={() => openActionDialog(orden, 'duplicar')}
                          >
                            Duplicar
                          </Button>

                          {!orden.tiene_documentos ? (
                            <Button
                              size="sm"
                              variant="outline"
                              className="border-destructive/40 text-destructive hover:bg-destructive/10"
                              disabled={updatingId === orden.id}
                              onClick={() => openActionDialog(orden, 'eliminar')}
                            >
                              Eliminar
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

      <TablePagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalRows={totalRows}
        pageSize={pageSize}
        onPrev={prevPage}
        onNext={nextPage}
      />

      <DocumentActionsDialog
        actionType={actionType}
        open={actionDialogOpen}
        loading={Boolean(actionItem && updatingId === actionItem.id)}
        value={actionReason}
        onChange={setActionReason}
        item={actionItem}
        onCancel={closeActionDialog}
        onConfirm={handleActionConfirm}
      />
    </section>
  )
}

export default ComprasOrdenesListPage
