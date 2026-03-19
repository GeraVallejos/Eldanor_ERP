import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import DocumentActionsDialog from '@/components/ui/DocumentActionsDialog'
import MenuButton from '@/components/ui/MenuButton'
import ReasonDialog from '@/components/ui/ReasonDialog'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import TablePagination from '@/components/ui/TablePagination'
import { useTableSorting } from '@/lib/tableSorting'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

const TIPO_LABELS = {
  GUIA_RECEPCION: 'Guía de recepción',
  FACTURA_COMPRA: 'Factura de compra',
  BOLETA_COMPRA: 'Boleta de compra',
}

const ESTADO_LABELS = {
  BORRADOR: 'Borrador',
  CONFIRMADO: 'Confirmado',
  ANULADO: 'Anulado',
}

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function ComprasDocumentosListPage() {
  const [status, setStatus] = useState('idle')
  const [documentos, setDocumentos] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [search, setSearch] = useState('')
  const [estadoFilter, setEstadoFilter] = useState('ACTIVOS')
  const [tipoFilter, setTipoFilter] = useState('ALL')
  const [updatingId, setUpdatingId] = useState(null)
  const [reasonDialogDoc, setReasonDialogDoc] = useState(null)
  const [correctionReason, setCorrectionReason] = useState('')
  const [actionDialogOpen, setActionDialogOpen] = useState(false)
  const [actionType, setActionType] = useState(null)
  const [actionItem, setActionItem] = useState(null)
  const [facturaConfirmDoc, setFacturaConfirmDoc] = useState(null)
  const [facturaEnTransito, setFacturaEnTransito] = useState(false)

  const loadData = async () => {
    setStatus('loading')
    try {
      const [{ data: docsData }, { data: provData }, { data: ctcData }] = await Promise.all([
        api.get('/documentos-compra/', { suppressGlobalErrorToast: true }),
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
      ])
      setDocumentos(normalizeListResponse(docsData))
      setProveedores(normalizeListResponse(provData))
      setContactos(normalizeListResponse(ctcData))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los documentos de compra.' }))
    }
  }

  useEffect(() => {
    const id = setTimeout(() => void loadData(), 0)
    return () => clearTimeout(id)
  }, [])

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

  const openCorrectionDialog = (doc) => {
    setReasonDialogDoc(doc)
    setCorrectionReason('')
  }

  const closeCorrectionDialog = () => {
    setReasonDialogDoc(null)
    setCorrectionReason('')
  }

  const openActionDialog = (doc, action) => {
    setActionItem(doc)
    setActionType(action)
    setActionDialogOpen(true)
  }

  const closeActionDialog = () => {
    setActionDialogOpen(false)
    setActionItem(null)
    setActionType(null)
  }

  const openFacturaConfirmDialog = (doc) => {
    setFacturaConfirmDoc(doc)
    setFacturaEnTransito(false)
  }

  const closeFacturaConfirmDialog = () => {
    setFacturaConfirmDoc(null)
    setFacturaEnTransito(false)
  }

  const handleActionConfirm = async () => {
    if (!actionItem || !actionType) return

    setUpdatingId(actionItem.id)
    try {
      const endpoint = `/documentos-compra/${actionItem.id}/`

      if (actionType === 'anular') {
        const { data } = await api.post(`${endpoint}anular/`, { motivo: 'Anulación desde lista' }, { suppressGlobalErrorToast: true })
        setDocumentos((prev) => prev.map((d) => (String(d.id) === String(actionItem.id) ? { ...d, ...data } : d)))
        toast.success('Documento anulado.')
      }

      closeActionDialog()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo completar la acción.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return documentos.filter((doc) => {
      if (estadoFilter === 'ACTIVOS' && doc.estado === 'ANULADO') {
        return false
      }

      if (estadoFilter !== 'ALL' && estadoFilter !== 'ACTIVOS' && doc.estado !== estadoFilter) {
        return false
      }
      if (tipoFilter !== 'ALL' && doc.tipo_documento !== tipoFilter) {
        return false
      }

      if (!query) {
        return true
      }

      const prov = proveedorById.get(String(doc.proveedor))
      const ctc = contactoById.get(String(prov?.contacto))
      return (
        String(doc.folio || '').toLowerCase().includes(query) ||
        String(doc.tipo_documento || '').toLowerCase().includes(query) ||
        String(doc.estado || '').toLowerCase().includes(query) ||
        String(ctc?.nombre || '').toLowerCase().includes(query)
      )
    })
  }, [documentos, search, estadoFilter, tipoFilter, proveedorById, contactoById])

  const { paginatedRows: paginatedDocumentos, toggleSort, getSortIndicator, currentPage, totalPages, totalRows, pageSize, nextPage, prevPage } = useTableSorting(filtered, {
    accessors: {
      creado_en: (doc) => doc.creado_en,
      tipo: (doc) => TIPO_LABELS[doc.tipo_documento] || doc.tipo_documento,
      folio: (doc) => doc.folio,
      proveedor: (doc) => {
        const prov = proveedorById.get(String(doc.proveedor))
        const ctc = contactoById.get(String(prov?.contacto))
        return ctc?.nombre || ''
      },
      fecha_emision: (doc) => doc.fecha_emision,
      estado: (doc) => ESTADO_LABELS[doc.estado] || doc.estado,
      total: (doc) => Number(doc.total || 0),
    },
    pageSize: 10,
    initialKey: 'creado_en',
    initialDirection: 'desc',
  })

  const handleAccion = async (doc, accion, options = {}) => {
    setUpdatingId(doc.id)
    try {
      let endpoint = ''
      let payload = {}

      if (accion === 'anular') {
        endpoint = `/documentos-compra/${doc.id}/anular/`
      } else if (accion === 'corregir') {
        const motivo = correctionReason
        if (!motivo || !motivo.trim()) {
          toast.error('Debes indicar un motivo para corregir.')
          return
        }
        endpoint = `/documentos-compra/${doc.id}/corregir/`
        payload = { motivo: motivo.trim() }
      } else if (accion === 'duplicar') {
        endpoint = `/documentos-compra/${doc.id}/duplicar/`
      } else {
        endpoint =
          doc.tipo_documento === 'GUIA_RECEPCION'
            ? `/documentos-compra/${doc.id}/confirmar_guia/`
            : `/documentos-compra/${doc.id}/confirmar_factura/`
        payload = {
          en_transito: Boolean(options.enTransito),
        }
      }

      const { data } = await api.post(endpoint, payload, { suppressGlobalErrorToast: true })

      if (accion === 'corregir') {
        toast.success('Documento corregido. Se creo un nuevo borrador.')
        closeCorrectionDialog()
        await loadData()
      } else if (accion === 'duplicar') {
        setDocumentos((prev) => [...prev, data])
        toast.success('Documento duplicado correctamente.')
      } else {
        setDocumentos((prev) => prev.map((d) => (String(d.id) === String(doc.id) ? { ...d, ...data } : d)))
        toast.success(
          accion === 'anular'
            ? 'Documento anulado.'
            : options.enTransito
            ? 'Documento confirmado en transito (sin ingreso a stock disponible).'
            : 'Documento confirmado.',
        )
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el documento.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  const getTodaySuffix = () => getChileDateSuffix()

  const handleExportExcel = async () => {
    if (filtered.length === 0) return
    await downloadExcelFile({
      sheetName: 'DocumentosCompra',
      fileName: `documentos_compra_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: 'Tipo', key: 'tipo', width: 22 },
        { header: 'Folio', key: 'folio', width: 16 },
        { header: 'Proveedor', key: 'proveedor', width: 32 },
        { header: 'Fecha emisión', key: 'fecha_emision', width: 18 },
        { header: 'Estado', key: 'estado', width: 16 },
        { header: 'Total', key: 'total', width: 16 },
      ],
      rows: filtered.map((doc) => {
        const prov = proveedorById.get(String(doc.proveedor))
        const ctc = contactoById.get(String(prov?.contacto))
        return {
          tipo: TIPO_LABELS[doc.tipo_documento] || doc.tipo_documento,
          folio: doc.folio || '-',
          proveedor: ctc?.nombre || '-',
          fecha_emision: formatDateChile(doc.fecha_emision),
          estado: ESTADO_LABELS[doc.estado] || doc.estado,
          total: Number(doc.total || 0),
        }
      }),
    })
  }

  const handleExportPdf = async () => {
    if (filtered.length === 0) return
    await downloadSimpleTablePdf({
      title: 'Documentos de compra',
      fileName: `documentos_compra_${getTodaySuffix()}.pdf`,
      headers: ['Tipo', 'Folio', 'Proveedor', 'Fecha emisión', 'Estado', 'Total'],
      rows: filtered.map((doc) => {
        const prov = proveedorById.get(String(doc.proveedor))
        const ctc = contactoById.get(String(prov?.contacto))
        return [
          TIPO_LABELS[doc.tipo_documento] || doc.tipo_documento,
          doc.folio || '-',
          ctc?.nombre || '-',
          formatDateChile(doc.fecha_emision),
          ESTADO_LABELS[doc.estado] || doc.estado,
          formatMoney(doc.total),
        ]
      }),
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Documentos de compra</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <MenuButton
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
            disabled={filtered.length === 0}
          />
          <Link
            to="/compras/ordenes"
            className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Ver ordenes
          </Link>
          <Link
            to="/compras/documentos/nuevo"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Nuevo documento
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 md:grid-cols-3 md:items-end">
        <label className="text-sm">
          Buscar
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Folio, proveedor, tipo o estado..."
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </label>

        <label className="text-sm">
          Estado
          <select
            value={estadoFilter}
            onChange={(e) => setEstadoFilter(e.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="ACTIVOS">Activos</option>
            <option value="ALL">Todos</option>
            <option value="BORRADOR">Borrador</option>
            <option value="CONFIRMADO">Confirmado</option>
            <option value="ANULADO">Anulado</option>
          </select>
        </label>

        <label className="text-sm">
          Tipo
          <select
            value={tipoFilter}
            onChange={(e) => setTipoFilter(e.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="ALL">Todos</option>
            <option value="FACTURA_COMPRA">Solo facturas</option>
            <option value="BOLETA_COMPRA">Solo boletas</option>
            <option value="GUIA_RECEPCION">Solo guías</option>
          </select>
        </label>
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando documentos...</p> : null}

      {status === 'succeeded' ? (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('tipo')} className="inline-flex items-center gap-1 hover:text-primary">
                    Tipo <span className="text-xs text-muted-foreground">{getSortIndicator('tipo')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('folio')} className="inline-flex items-center gap-1 hover:text-primary">
                    Folio <span className="text-xs text-muted-foreground">{getSortIndicator('folio')}</span>
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
                <th className="px-3 py-2 text-right font-medium">
                  <button type="button" onClick={() => toggleSort('total')} className="inline-flex items-center gap-1 hover:text-primary">
                    Total <span className="text-xs text-muted-foreground">{getSortIndicator('total')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={7}>
                    No hay documentos de compra.
                  </td>
                </tr>
              ) : (
                paginatedDocumentos.map((doc) => {
                  const prov = proveedorById.get(String(doc.proveedor))
                  const ctc = contactoById.get(String(prov?.contacto))
                  const isBusy = updatingId === doc.id

                  return (
                    <tr key={doc.id} className="border-t border-border">
                      <td className="px-3 py-2">{TIPO_LABELS[doc.tipo_documento] || doc.tipo_documento}</td>
                      <td className="px-3 py-2">{doc.folio}</td>
                      <td className="px-3 py-2">{ctc?.nombre || '-'}</td>
                      <td className="px-3 py-2">{formatDateChile(doc.fecha_emision)}</td>
                      <td className="px-3 py-2">{ESTADO_LABELS[doc.estado] || doc.estado}</td>
                      <td className="px-3 py-2 text-right">{formatMoney(doc.total)}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap justify-end gap-1">
                          <Link
                            to={`/compras/documentos/${doc.id}`}
                            className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'text-xs')}
                          >
                            Ver
                          </Link>
                          {doc.estado === 'BORRADOR' ? (
                            <>
                              <Link
                                to={`/compras/documentos/${doc.id}/editar`}
                                className={cn(
                                  buttonVariants({ variant: 'outline', size: 'sm' }),
                                  'text-xs',
                                )}
                              >
                                Editar
                              </Link>
                              <Button
                                variant="default"
                                size="sm"
                                className="text-xs"
                                disabled={isBusy}
                                onClick={() => {
                                  if (doc.tipo_documento === 'FACTURA_COMPRA' || doc.tipo_documento === 'BOLETA_COMPRA') {
                                    openFacturaConfirmDialog(doc)
                                    return
                                  }
                                  void handleAccion(doc, 'confirmar')
                                }}
                              >
                                {isBusy ? 'Procesando...' : 'Confirmar'}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-xs"
                                disabled={isBusy}
                                onClick={() => handleAccion(doc, 'duplicar')}
                              >
                                {isBusy ? 'Procesando...' : 'Duplicar'}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 border-destructive/40 px-3 text-xs text-destructive hover:bg-destructive/10"
                                disabled={isBusy}
                                onClick={() => openActionDialog(doc, 'anular')}
                              >
                                Anular
                              </Button>
                            </>
                          ) : doc.estado === 'CONFIRMADO' ? (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-xs"
                                disabled={isBusy}
                                onClick={() => openCorrectionDialog(doc)}
                              >
                                {isBusy ? 'Procesando...' : 'Corregir'}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-xs"
                                disabled={isBusy}
                                onClick={() => handleAccion(doc, 'duplicar')}
                              >
                                {isBusy ? 'Procesando...' : 'Duplicar'}
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 border-destructive/40 px-3 text-xs text-destructive hover:bg-destructive/10"
                                disabled={isBusy}
                                onClick={() => openActionDialog(doc, 'anular')}
                              >
                                {isBusy ? 'Procesando...' : 'Anular'}
                              </Button>
                            </>
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

      {status === 'failed' ? (
        <p className="text-sm text-destructive">Error al cargar los documentos de compra.</p>
      ) : null}

      <ReasonDialog
        open={Boolean(reasonDialogDoc)}
        title="Corregir documento"
        description={
          reasonDialogDoc
            ? `Se anulara el documento ${reasonDialogDoc.folio} y se creara un nuevo borrador.`
            : ''
        }
        value={correctionReason}
        onChange={setCorrectionReason}
        loading={Boolean(reasonDialogDoc) && updatingId === reasonDialogDoc.id}
        confirmLabel="Corregir"
        onCancel={closeCorrectionDialog}
        onConfirm={() => {
          if (reasonDialogDoc) {
            void handleAccion(reasonDialogDoc, 'corregir')
          }
        }}
      />

      <DocumentActionsDialog
        actionType={actionType}
        open={actionDialogOpen}
        loading={Boolean(actionItem && updatingId === actionItem.id)}
        item={actionItem}
        onCancel={closeActionDialog}
        onConfirm={handleActionConfirm}
      />

      {facturaConfirmDoc ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-lg bg-background p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold">
              Confirmar {facturaConfirmDoc.tipo_documento === 'BOLETA_COMPRA' ? 'boleta' : 'factura'} de compra
            </h3>
            <p className="text-sm text-muted-foreground">
              Define como impactara inventario el documento {facturaConfirmDoc.folio || '-'}. Si ya hubo ingreso fisico por GD/recepcion,
              el sistema solo movera pendiente para evitar duplicados.
            </p>

            <label className="flex items-start gap-2 rounded-md border border-border p-3">
              <input
                type="radio"
                name="factura-flujo"
                checked={!facturaEnTransito}
                onChange={() => setFacturaEnTransito(false)}
                className="mt-1"
              />
              <span className="text-sm">
                <span className="font-medium">Ingreso normal</span>
                <br />
                Confirma la factura y registra entrada a inventario disponible (solo pendiente de OC si aplica).
              </span>
            </label>

            <label className="flex items-start gap-2 rounded-md border border-border p-3">
              <input
                type="radio"
                name="factura-flujo"
                checked={facturaEnTransito}
                onChange={() => setFacturaEnTransito(true)}
                className="mt-1"
              />
              <span className="text-sm">
                <span className="font-medium">Factura en transito</span>
                <br />
                Confirma documento tributario, pero sin mover stock disponible todavia.
              </span>
            </label>

            <div className="flex justify-end gap-2">
              <Button variant="outline" size="md" onClick={closeFacturaConfirmDialog}>
                Cancelar
              </Button>
              <Button
                variant="default"
                size="md"
                disabled={updatingId === facturaConfirmDoc.id}
                onClick={async () => {
                  await handleAccion(facturaConfirmDoc, 'confirmar', { enTransito: facturaEnTransito })
                  closeFacturaConfirmDialog()
                }}
              >
                {updatingId === facturaConfirmDoc.id ? 'Procesando...' : 'Confirmar documento'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default ComprasDocumentosListPage
