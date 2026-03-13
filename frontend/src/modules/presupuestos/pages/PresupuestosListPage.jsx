import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { pdf } from '@react-pdf/renderer'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import TablePagination from '@/components/ui/TablePagination'
import { useTableSorting } from '@/lib/tableSorting'
import { cn } from '@/lib/utils'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import PresupuestoPdfDocument from '@/modules/presupuestos/components/PresupuestoPdfDocument'
import { canManagePresupuestoStatus, hasPermission } from '@/modules/shared/auth/permissions'
import { getCompanyDocumentBranding } from '@/modules/shared/documents/companyBranding'

const FALLBACK_STATUS_LABELS = {
  BORRADOR: 'Borrador',
  ENVIADO: 'Enviado',
  APROBADO: 'Aprobado',
  RECHAZADO: 'Rechazado',
  ANULADO: 'Anulado',
}

const FALLBACK_STATUS_TRANSITIONS = {
  BORRADOR: ['ENVIADO', 'APROBADO'],
  ENVIADO: ['BORRADOR', 'APROBADO', 'RECHAZADO'],
  RECHAZADO: ['BORRADOR', 'ENVIADO'],
  APROBADO: ['ANULADO'],
  ANULADO: [],
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

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function PresupuestosListPage() {
  const currentUser = useSelector(selectCurrentUser)
  const [presupuestos, setPresupuestos] = useState([])
  const [clientes, setClientes] = useState([])
  const [contactos, setContactos] = useState([])
  const [status, setStatus] = useState('idle')
  const [statusLabels, setStatusLabels] = useState(FALLBACK_STATUS_LABELS)
  const [statusTransitions, setStatusTransitions] = useState(FALLBACK_STATUS_TRANSITIONS)
  const [allStatusCodes, setAllStatusCodes] = useState(Object.keys(FALLBACK_STATUS_LABELS))
  const [deletingId, setDeletingId] = useState(null)
  const [generatingPdfId, setGeneratingPdfId] = useState(null)
  const [changingStatusId, setChangingStatusId] = useState(null)
  const [presupuestoToChangeStatus, setPresupuestoToChangeStatus] = useState(null)
  const [nextStatusValue, setNextStatusValue] = useState('')
  const [presupuestoToDelete, setPresupuestoToDelete] = useState(null)

  const loadData = async () => {
    setStatus('loading')

    try {
      const [{ data: presupuestosData }, { data: clientesData }, { data: contactosData }, { data: catalogData }] =
        await Promise.all([
        api.get('/presupuestos/', { suppressGlobalErrorToast: true }),
        api.get('/clientes/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
        api.get('/presupuestos/catalogo-estados/', { suppressGlobalErrorToast: true }),
      ])

      setPresupuestos(normalizeListResponse(presupuestosData))
      setClientes(normalizeListResponse(clientesData))
      setContactos(normalizeListResponse(contactosData))

      const estadosCatalogo = Array.isArray(catalogData?.estados) ? catalogData.estados : []
      if (estadosCatalogo.length > 0) {
        const labels = {}
        const codes = []

        estadosCatalogo.forEach((estado) => {
          const code = String(estado?.value || '').toUpperCase()
          if (!code) {
            return
          }
          labels[code] = estado?.label || code
          codes.push(code)
        })

        if (Object.keys(labels).length > 0) {
          setStatusLabels(labels)
          setAllStatusCodes(codes)
        }
      }

      const transicionesCatalogo = catalogData?.transiciones
      if (transicionesCatalogo && typeof transicionesCatalogo === 'object') {
        setStatusTransitions(transicionesCatalogo)
      }

      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los presupuestos.' }))
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  const clienteById = useMemo(() => {
    const map = new Map()
    clientes.forEach((cliente) => {
      map.set(String(cliente.id), cliente)
    })
    return map
  }, [clientes])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => {
      map.set(String(contacto.id), contacto)
    })
    return map
  }, [contactos])

  const resolveClienteNombre = (clienteId) => {
    const cliente = clienteById.get(String(clienteId))
    const contacto = contactoById.get(String(cliente?.contacto))
    return contacto?.nombre || `Cliente #${clienteId}`
  }

  const { paginatedRows: paginatedPresupuestos, toggleSort, getSortIndicator, currentPage, totalPages, totalRows, pageSize, nextPage, prevPage } = useTableSorting(presupuestos, {
    accessors: {
      creado_en: (presupuesto) => presupuesto.creado_en,
      numero: (presupuesto) => presupuesto.numero,
      cliente: (presupuesto) => resolveClienteNombre(presupuesto.cliente),
      fecha: (presupuesto) => presupuesto.fecha,
      fecha_vencimiento: (presupuesto) => presupuesto.fecha_vencimiento,
      estado: (presupuesto) => resolveStatusLabel(presupuesto.estado),
      total: (presupuesto) => Number(presupuesto.total ?? 0),
    },
    initialKey: 'creado_en',
    initialDirection: 'desc',
  })

  const requestDeletePresupuesto = (presupuesto) => {
    setPresupuestoToDelete(presupuesto)
  }

  const canEditPresupuesto = hasPermission(currentUser, 'PRESUPUESTOS.EDITAR')
  const canDeletePresupuesto = hasPermission(currentUser, 'PRESUPUESTOS.BORRAR')
  const canCreatePresupuesto = hasPermission(currentUser, 'PRESUPUESTOS.CREAR')

  const resolveStatusLabel = (statusCode) => {
    const normalized = String(statusCode || '').toUpperCase()
    return statusLabels[normalized] || normalized || '-'
  }

  const getStatusOptions = (presupuesto) => {
    const currentStatus = String(presupuesto?.estado || '').toUpperCase()
    const availableTransitions = statusTransitions[currentStatus] || []

    return availableTransitions
      .filter((targetStatus) => canManagePresupuestoStatus(currentUser, currentStatus, targetStatus))
      .map((targetStatus) => ({
        value: targetStatus,
        label: resolveStatusLabel(targetStatus),
      }))
  }

  const openStatusModal = (presupuesto) => {
    const statusOptions = getStatusOptions(presupuesto)
    setPresupuestoToChangeStatus(presupuesto)
    setNextStatusValue(statusOptions[0]?.value || '')
  }

  const closeStatusModal = ({ force = false } = {}) => {
    if (!force && changingStatusId) {
      return
    }

    setPresupuestoToChangeStatus(null)
    setNextStatusValue('')
  }

  const applyStatusChange = async () => {
    const presupuesto = presupuestoToChangeStatus
    const nextStatus = nextStatusValue

    if (!presupuesto?.id) {
      return
    }

    if (!nextStatus) {
      return
    }

    setChangingStatusId(presupuesto.id)

    try {
      const { data } = await api.post(
        `/presupuestos/${presupuesto.id}/cambiar_estado/`,
        { estado: nextStatus },
        { suppressGlobalErrorToast: true },
      )

      const { data: presupuestoRefrescado } = await api.get(`/presupuestos/${presupuesto.id}/`, {
        suppressGlobalErrorToast: true,
      })

      setPresupuestos((current) =>
        current.map((row) =>
          String(row.id) === String(presupuesto.id)
            ? { ...row, ...(presupuestoRefrescado || data || {}) }
            : row,
        ),
      )

      toast.success(`Estado actualizado a ${resolveStatusLabel(data?.estado || nextStatus)}.`)
      closeStatusModal({ force: true })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cambiar el estado del presupuesto.' }))
    } finally {
      setChangingStatusId(null)
    }
  }

  const confirmDeletePresupuesto = async () => {
    const presupuesto = presupuestoToDelete
    if (!presupuesto?.id) {
      return
    }

    setDeletingId(presupuesto.id)

    try {
      await api.delete(`/presupuestos/${presupuesto.id}/`, { suppressGlobalErrorToast: true })
      toast.success('Presupuesto eliminado correctamente.')
      setPresupuestoToDelete(null)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el presupuesto.' }))
    } finally {
      setDeletingId(null)
    }
  }

  const getPdfFileName = (presupuesto) => {
    const rawNumber = presupuesto?.numero ? String(presupuesto.numero) : String(presupuesto?.id || 'presupuesto')
    const safeNumber = rawNumber.replace(/[^a-zA-Z0-9_-]/g, '')
    return `presupuesto-${safeNumber || 'documento'}.pdf`
  }

  const downloadPresupuestoPdf = async (presupuesto) => {
    if (!presupuesto?.id) {
      return
    }

    setGeneratingPdfId(presupuesto.id)

    try {
      const [{ data: presupuestoData }, { data: itemsData }] = await Promise.all([
        api.get(`/presupuestos/${presupuesto.id}/`, { suppressGlobalErrorToast: true }),
        api.get('/presupuesto-items/', { suppressGlobalErrorToast: true }),
      ])

      const branding = await getCompanyDocumentBranding({ user: currentUser })

      const presupuestoActual = presupuestoData || presupuesto
      const items = normalizeListResponse(itemsData).filter(
        (item) => String(item.presupuesto) === String(presupuesto.id),
      )

      const cliente = clienteById.get(String(presupuestoActual.cliente))
      const contacto = contactoById.get(String(cliente?.contacto || ''))

      const pdfDocument = (
        <PresupuestoPdfDocument
          presupuesto={presupuestoActual}
          items={items}
          empresa={{
            nombre: branding?.nombre || currentUser?.empresa_nombre || 'Mi Empresa',
            logo: branding?.logo || null,
          }}
          cliente={{
            nombre: contacto?.nombre || `Cliente #${presupuestoActual.cliente}`,
            rut: contacto?.rut || '',
            email: contacto?.email || '',
          }}
        />
      )

      const blob = await pdf(pdfDocument).toBlob()
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = getPdfFileName(presupuestoActual)
      link.click()
      URL.revokeObjectURL(blobUrl)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo generar el PDF del presupuesto.' }))
    } finally {
      setGeneratingPdfId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Presupuestos</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          {canCreatePresupuesto ? (
            <Link
              to="/presupuestos/nuevo"
              className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
            >
              Nuevo presupuesto
            </Link>
          ) : null}
        </div>
      </div>

      {status === 'loading' && <p className="text-sm text-muted-foreground">Cargando presupuestos...</p>}

      {status === 'succeeded' && (
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
                  <button type="button" onClick={() => toggleSort('cliente')} className="inline-flex items-center gap-1 hover:text-primary">
                    Cliente <span className="text-xs text-muted-foreground">{getSortIndicator('cliente')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('fecha')} className="inline-flex items-center gap-1 hover:text-primary">
                    Fecha <span className="text-xs text-muted-foreground">{getSortIndicator('fecha')}</span>
                  </button>
                </th>
                <th className="px-3 py-2 text-left font-medium">
                  <button type="button" onClick={() => toggleSort('fecha_vencimiento')} className="inline-flex items-center gap-1 hover:text-primary">
                    Vencimiento <span className="text-xs text-muted-foreground">{getSortIndicator('fecha_vencimiento')}</span>
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
                <th className="px-2 py-2 text-right font-medium" style={{ minWidth: '280px' }}>
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody>
              {presupuestos.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={7}>
                    No hay presupuestos cargados.
                  </td>
                </tr>
              ) : (
                paginatedPresupuestos.map((presupuesto) => {
                  const statusOptions = getStatusOptions(presupuesto)
                  const isStatusUpdating = changingStatusId === presupuesto.id

                  return (
                    <tr key={presupuesto.id} className="border-t border-border">
                    <td className="px-3 py-2">{presupuesto.numero}</td>
                    <td className="px-3 py-2">{resolveClienteNombre(presupuesto.cliente)}</td>
                    <td className="px-3 py-2">{presupuesto.fecha || '-'}</td>
                    <td className="px-3 py-2">{presupuesto.fecha_vencimiento || '-'}</td>
                    <td className="px-3 py-2">{resolveStatusLabel(presupuesto.estado)}</td>
                    <td className="px-3 py-2">{formatMoney(presupuesto.total ?? 0)}</td>
                    <td className="px-2 py-2" style={{ minWidth: '280px' }}>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {canEditPresupuesto ? (
                          <Link
                            to={`/presupuestos/${presupuesto.id}/editar`}
                            className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-7 px-2 text-xs')}
                          >
                            Editar
                          </Link>
                        ) : null}
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={generatingPdfId === presupuesto.id}
                          onClick={() => downloadPresupuestoPdf(presupuesto)}
                          className="h-7 px-2 text-xs"
                        >
                          {generatingPdfId === presupuesto.id ? 'Generando...' : 'PDF'}
                        </Button>

                        {statusOptions.length > 0 ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={isStatusUpdating}
                            onClick={() => openStatusModal(presupuesto)}
                            className="h-7 px-2 text-xs"
                          >
                            {isStatusUpdating ? 'Guardando...' : 'Cambiar estado'}
                          </Button>
                        ) : null}

                        {canDeletePresupuesto ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deletingId === presupuesto.id}
                            onClick={() => requestDeletePresupuesto(presupuesto)}
                            className="h-7 border-destructive/40 px-2 text-xs text-destructive hover:bg-destructive/10"
                          >
                            {deletingId === presupuesto.id ? 'Eliminando...' : 'Eliminar'}
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
      )}

      <TablePagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalRows={totalRows}
        pageSize={pageSize}
        onPrev={prevPage}
        onNext={nextPage}
      />

      <ConfirmDialog
        open={Boolean(presupuestoToDelete)}
        title="Eliminar presupuesto"
        description={
          presupuestoToDelete
            ? `Se eliminara el presupuesto Nro ${presupuestoToDelete.numero}. Esta accion no se puede deshacer.`
            : ''
        }
        confirmLabel="Eliminar"
        loading={deletingId === presupuestoToDelete?.id}
        onCancel={() => {
          if (!deletingId) {
            setPresupuestoToDelete(null)
          }
        }}
        onConfirm={confirmDeletePresupuesto}
      />

      {presupuestoToChangeStatus ? (
        <div className="fixed inset-0 z-90 flex items-center justify-center bg-foreground/40 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-4 shadow-xl">
            <h3 className="text-lg font-semibold">Cambiar estado de presupuesto</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Presupuesto Nro {presupuestoToChangeStatus.numero} ({resolveStatusLabel(presupuestoToChangeStatus.estado)}).
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Estados disponibles en el sistema: {allStatusCodes.map((code) => resolveStatusLabel(code)).join(', ')}
            </p>

            <div className="mt-4 space-y-2">
              <label htmlFor="estado-presupuesto" className="text-sm font-medium">
                Nuevo estado
              </label>
              <select
                id="estado-presupuesto"
                value={nextStatusValue}
                onChange={(event) => setNextStatusValue(event.target.value)}
                disabled={changingStatusId === presupuestoToChangeStatus.id}
                className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
              >
                {getStatusOptions(presupuestoToChangeStatus).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <Button type="button" variant="outline" onClick={closeStatusModal} disabled={changingStatusId !== null}>
                Cancelar
              </Button>
              <Button
                type="button"
                onClick={applyStatusChange}
                disabled={!nextStatusValue || changingStatusId !== null}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {changingStatusId === presupuestoToChangeStatus.id ? 'Guardando...' : 'Confirmar cambio'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default PresupuestosListPage
