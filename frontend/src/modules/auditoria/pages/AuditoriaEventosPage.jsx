import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'sonner'

import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import {
  clearAuditoriaFilters,
  selectAuditoriaEventos,
  selectAuditoriaFilters,
  selectAuditoriaIntegrity,
  selectAuditoriaPagination,
  selectAuditoriaStatus,
  selectAuditoriaSubmittedFilters,
  setAuditoriaError,
  setAuditoriaEventos,
  setAuditoriaFilters,
  setAuditoriaIntegrity,
  setAuditoriaPagination,
  setAuditoriaStatus,
  setAuditoriaSubmittedFilters,
} from '@/modules/auditoria/store/auditoriaSlice'
import Button from '@/components/ui/Button'
import ExportMenuButton from '@/components/ui/ExportMenuButton'
import SearchableSelect from '@/components/ui/SearchableSelect'
import TablePagination from '@/components/ui/TablePagination'
import { formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

const ACTION_LABELS = {
  VER: 'Ver',
  CREAR: 'Crear',
  EDITAR: 'Editar',
  APROBAR: 'Aprobar',
  ANULAR: 'Anular',
  BORRAR: 'Borrar',
  EMITIR: 'Emitir',
  COBRAR: 'Cobrar',
  PAGAR: 'Pagar',
  CONCILIAR: 'Conciliar',
  CONTABILIZAR: 'Contabilizar',
  GESTIONAR_PERMISOS: 'Gestionar permisos',
}

const SEVERITY_OPTIONS = [
  { value: 'INFO', label: 'Informativo' },
  { value: 'WARNING', label: 'Advertencia' },
  { value: 'ERROR', label: 'Error' },
  { value: 'CRITICAL', label: 'Critico' },
]

function makeActions(codes) {
  return codes.map((code) => ({ value: code, label: ACTION_LABELS[code] ?? code }))
}

const MODULE_OPTIONS = [
  { value: 'AUDITORIA', label: 'Auditoria' },
  { value: 'PRESUPUESTOS', label: 'Presupuestos' },
  { value: 'PRODUCTOS', label: 'Productos' },
  { value: 'CONTACTOS', label: 'Contactos' },
  { value: 'INVENTARIO', label: 'Inventario' },
  { value: 'COMPRAS', label: 'Compras' },
  { value: 'ADMINISTRACION', label: 'Administracion' },
  { value: 'VENTAS', label: 'Ventas' },
  { value: 'FACTURACION', label: 'Facturacion' },
  { value: 'TESORERIA', label: 'Tesoreria' },
  { value: 'CONTABILIDAD', label: 'Contabilidad' },
]

const MODULE_METADATA = {
  AUDITORIA: {
    actions: makeActions(['VER']),
    eventTypes: [],
    entityTypes: [],
  },
  PRESUPUESTOS: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'APROBAR', 'ANULAR', 'BORRAR']),
    eventTypes: [
      { value: 'PRESUPUESTO_ESTADO_BORRADOR', label: 'Volvio a borrador' },
      { value: 'PRESUPUESTO_ESTADO_ENVIADO', label: 'Enviado al cliente' },
      { value: 'PRESUPUESTO_ESTADO_APROBADO', label: 'Presupuesto aprobado' },
      { value: 'PRESUPUESTO_ESTADO_RECHAZADO', label: 'Presupuesto rechazado' },
      { value: 'PRESUPUESTO_ESTADO_ANULADO', label: 'Presupuesto anulado' },
    ],
    entityTypes: [{ value: 'PRESUPUESTO', label: 'Presupuesto' }],
  },
  PRODUCTOS: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'BORRAR']),
    eventTypes: [],
    entityTypes: [],
  },
  INVENTARIO: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'BORRAR']),
    eventTypes: [{ value: 'INVENTARIO_MOVIMIENTO_REGISTRADO', label: 'Movimiento de inventario registrado' }],
    entityTypes: [{ value: 'MOVIMIENTO_INVENTARIO', label: 'Movimiento de inventario' }],
  },
  COMPRAS: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'APROBAR', 'ANULAR', 'BORRAR']),
    eventTypes: [
      { value: 'OC_CREADA', label: 'Orden de compra creada' },
      { value: 'OC_ACTUALIZADA', label: 'Orden de compra actualizada' },
      { value: 'OC_ELIMINADA', label: 'Orden de compra eliminada' },
      { value: 'DOCUMENTO_COMPRA_CREADO', label: 'Documento de compra creado' },
      { value: 'DOCUMENTO_COMPRA_ACTUALIZADO', label: 'Documento de compra actualizado' },
      { value: 'DOCUMENTO_COMPRA_ELIMINADO', label: 'Documento de compra eliminado' },
      { value: 'RECEPCION_CREADA', label: 'Recepcion de compra creada' },
      { value: 'RECEPCION_ACTUALIZADA', label: 'Recepcion de compra actualizada' },
      { value: 'RECEPCION_ELIMINADA', label: 'Recepcion de compra eliminada' },
      { value: 'COMPRA_GUIA_CONFIRMADA', label: 'Guia de despacho confirmada' },
      { value: 'COMPRA_FACTURA_CONFIRMADA_TRANSITO', label: 'Factura en transito confirmada' },
      { value: 'COMPRA_FACTURA_CONFIRMADA', label: 'Factura confirmada' },
      { value: 'COMPRA_DOCUMENTO_ANULADO', label: 'Documento de compra anulado' },
      { value: 'COMPRA_DOCUMENTO_CORREGIDO', label: 'Documento de compra corregido' },
      { value: 'COMPRA_DOCUMENTO_DUPLICADO', label: 'Documento de compra duplicado' },
    ],
    entityTypes: [
      { value: 'ORDENCOMPRA', label: 'Orden de compra' },
      { value: 'DOCUMENTOCOMPRAPROVEEDOR', label: 'Documento de proveedor' },
      { value: 'RECEPCIONCOMPRA', label: 'Recepcion de compra' },
    ],
  },
  CONTACTOS: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'BORRAR']),
    eventTypes: [
      { value: 'CONTACTO_CREADO', label: 'Contacto creado' },
      { value: 'CONTACTO_ACTUALIZADO', label: 'Contacto actualizado' },
      { value: 'CONTACTO_ELIMINADO', label: 'Contacto eliminado' },
      { value: 'CLIENTE_CREADO', label: 'Cliente creado' },
      { value: 'CLIENTE_ACTUALIZADO', label: 'Cliente actualizado' },
      { value: 'CLIENTE_ELIMINADO', label: 'Cliente eliminado' },
      { value: 'PROVEEDOR_CREADO', label: 'Proveedor creado' },
      { value: 'PROVEEDOR_ACTUALIZADO', label: 'Proveedor actualizado' },
      { value: 'PROVEEDOR_ELIMINADO', label: 'Proveedor eliminado' },
      { value: 'CONTACTOS_BULK_IMPORT', label: 'Importacion masiva' },
    ],
    entityTypes: [
      { value: 'CONTACTO', label: 'Contacto' },
      { value: 'CLIENTE', label: 'Cliente' },
      { value: 'PROVEEDOR', label: 'Proveedor' },
    ],
  },
  ADMINISTRACION: {
    actions: makeActions(['VER', 'GESTIONAR_PERMISOS']),
    eventTypes: [],
    entityTypes: [],
  },
  VENTAS: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'ANULAR']),
    eventTypes: [],
    entityTypes: [],
  },
  FACTURACION: {
    actions: makeActions(['VER', 'CREAR', 'EDITAR', 'EMITIR', 'ANULAR']),
    eventTypes: [],
    entityTypes: [],
  },
  TESORERIA: {
    actions: makeActions(['VER', 'COBRAR', 'PAGAR', 'CONCILIAR']),
    eventTypes: [],
    entityTypes: [],
  },
  CONTABILIDAD: {
    actions: makeActions(['VER', 'CONTABILIZAR']),
    eventTypes: [],
    entityTypes: [],
  },
}

// Mapas planos para mostrar etiquetas en la tabla (todos los modulos)
const ALL_EVENT_TYPE_LABELS = Object.fromEntries(
  Object.values(MODULE_METADATA).flatMap((m) => m.eventTypes.map((e) => [e.value, e.label]))
)
const ALL_ENTITY_TYPE_LABELS = Object.fromEntries(
  Object.values(MODULE_METADATA).flatMap((m) => m.entityTypes.map((e) => [e.value, e.label]))
)
const MODULE_LABEL = Object.fromEntries(MODULE_OPTIONS.map((o) => [o.value, o.label]))
const SEVERITY_LABEL = Object.fromEntries(SEVERITY_OPTIONS.map((o) => [o.value, o.label]))
const DOCUMENT_TYPE_LABELS = {
  GUIA_RECEPCION: 'Guia de recepcion',
  FACTURA_COMPRA: 'Factura de compra',
}

function isUuidLike(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ''))
}

function resolveEntityLabel(row) {
  const payload = row?.payload || {}
  const meta = row?.meta || {}
  const baseLabel = ALL_ENTITY_TYPE_LABELS[row?.entity_type] ?? row?.entity_type ?? '-'

  const tipoDocumentoCode = payload?.tipo_documento || meta?.documento_tipo
  const tipoDocumentoLabel = payload?.tipo_documento_label || DOCUMENT_TYPE_LABELS[tipoDocumentoCode] || ''
  const folio = payload?.folio || meta?.folio || ''
  const numero = payload?.numero || ''

  if (tipoDocumentoLabel || folio || numero) {
    const parts = [tipoDocumentoLabel || baseLabel]
    if (folio) {
      parts.push(`Folio ${folio}`)
    }
    if (numero) {
      parts.push(`Nro ${numero}`)
    }
    return parts.join(' · ')
  }

  if (row?.entity_id && !isUuidLike(row.entity_id)) {
    return `${baseLabel} #${row.entity_id}`
  }

  return baseLabel
}

function resolveCompactEntityLabel(row) {
  const payload = row?.payload || {}
  const meta = row?.meta || {}
  const baseLabel = ALL_ENTITY_TYPE_LABELS[row?.entity_type] ?? row?.entity_type ?? '-'

  const tipoDocumentoCode = payload?.tipo_documento || meta?.documento_tipo
  const tipoDocumentoLabel = payload?.tipo_documento_label || DOCUMENT_TYPE_LABELS[tipoDocumentoCode] || ''
  const folio = payload?.folio || meta?.folio || ''
  const numero = payload?.numero || ''

  if (tipoDocumentoLabel || folio || numero) {
    const parts = [tipoDocumentoLabel || baseLabel]
    if (folio) {
      parts.push(`Folio ${folio}`)
    }
    if (numero) {
      parts.push(`Nro ${numero}`)
    }
    return parts.join(' · ')
  }

  return baseLabel
}

function normalizePagedResponse(data) {
  if (Array.isArray(data)) {
    return {
      count: data.length,
      next: null,
      previous: null,
      results: data,
    }
  }

  if (Array.isArray(data?.results)) {
    return {
      count: Number(data?.count || 0),
      next: data?.next || null,
      previous: data?.previous || null,
      results: data.results,
    }
  }

  return {
    count: 0,
    next: null,
    previous: null,
    results: [],
  }
}

function AuditoriaEventosPage() {
  const dispatch = useDispatch()
  const rows = useSelector(selectAuditoriaEventos)
  const pagination = useSelector(selectAuditoriaPagination)
  const filters = useSelector(selectAuditoriaFilters)
  const submittedFilters = useSelector(selectAuditoriaSubmittedFilters)
  const integrity = useSelector(selectAuditoriaIntegrity)
  const status = useSelector(selectAuditoriaStatus)
  const loading = status === 'loading'
  const [checkingIntegrity, setCheckingIntegrity] = useState(false)

  const activeFilters = useMemo(() => {
    const params = {}
    Object.entries(submittedFilters).forEach(([key, value]) => {
      if (String(value || '').trim()) {
        params[key] = String(value).trim()
      }
    })
    return params
  }, [submittedFilters])

  const fetchEventos = useCallback(async () => {
    dispatch(setAuditoriaStatus('loading'))
    dispatch(setAuditoriaError(null))
    try {
      const { data } = await api.get('/auditoria/eventos/', {
        params: activeFilters,
        suppressGlobalErrorToast: true,
      })
      const normalized = normalizePagedResponse(data)
      dispatch(setAuditoriaEventos(normalized.results))
      dispatch(setAuditoriaPagination({
        count: normalized.count,
        next: normalized.next,
        previous: normalized.previous,
      }))
      dispatch(setAuditoriaStatus('succeeded'))
    } catch (error) {
      dispatch(setAuditoriaStatus('failed'))
      dispatch(setAuditoriaError(normalizeApiError(error, { fallback: 'No se pudieron cargar los eventos de auditoria.' })))
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los eventos de auditoria.' }))
    }
  }, [activeFilters, dispatch])

  const checkIntegrity = useCallback(async () => {
    setCheckingIntegrity(true)
    try {
      const { data } = await api.get('/auditoria/eventos/integridad/', {
        suppressGlobalErrorToast: true,
      })
      dispatch(setAuditoriaIntegrity(data))
      if (data?.is_valid) {
        toast.success('Cadena de auditoria valida.')
      } else {
        toast.error('Se detectaron inconsistencias en la cadena de auditoria.')
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo verificar la integridad de auditoria.' }))
    } finally {
      setCheckingIntegrity(false)
    }
  }, [dispatch])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void fetchEventos()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [fetchEventos])

  const updateFilter = (key, value) => {
    if (key === 'module_code') {
      // Al cambiar el modulo se limpian los filtros derivados para evitar valores inconsistentes
      dispatch(setAuditoriaFilters({
        module_code: value,
        action_code: '',
        event_type: '',
        entity_type: '',
        page: 1,
      }))
    } else {
      dispatch(setAuditoriaFilters({ [key]: value, page: 1 }))
    }
  }

  const clearFilters = () => {
    dispatch(clearAuditoriaFilters())
    dispatch(setAuditoriaIntegrity(null))
  }

  const totalRows = Number(pagination.count || 0)
  const currentPage = Number(submittedFilters.page || 1)
  const pageSize = Number(submittedFilters.page_size || 8)
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize))

  const submitWithPage = (nextPage) => {
    const next = {
      ...filters,
      page: nextPage,
    }
    dispatch(setAuditoriaFilters(next))
    dispatch(setAuditoriaSubmittedFilters(next))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    submitWithPage(1)
  }

  const handleExportExcel = async () => {
    if (rows.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'Auditoria',
      fileName: `auditoria_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Fecha', key: 'fecha', width: 22 },
        { header: 'Modulo', key: 'module_code', width: 18 },
        { header: 'Accion', key: 'action_code', width: 16 },
        { header: 'Evento', key: 'event_type', width: 28 },
        { header: 'Entidad', key: 'entity', width: 24 },
        { header: 'Severidad', key: 'severity', width: 12 },
        { header: 'Usuario', key: 'usuario', width: 28 },
        { header: 'Resumen', key: 'summary', width: 48 },
      ],
      rows: rows.map((row) => ({
        fecha: formatDateTimeChile(row.occurred_at || row.creado_en),
        module_code: MODULE_LABEL[row.module_code] ?? row.module_code ?? '-',
        action_code: ACTION_LABELS[row.action_code] ?? row.action_code ?? '-',
        event_type: ALL_EVENT_TYPE_LABELS[row.event_type] ?? row.event_type ?? '-',
        entity: resolveEntityLabel(row),
        severity: SEVERITY_LABEL[row.severity] ?? row.severity ?? '-',
        usuario: row.creado_por_email || '-',
        summary: row.summary || '-',
      })),
    })
  }

  const handleExportPdf = async () => {
    if (rows.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Auditoria central ERP',
      fileName: `auditoria_${getChileDateSuffix()}.pdf`,
      headers: ['Fecha', 'Modulo', 'Accion', 'Evento', 'Entidad', 'Severidad'],
      rows: rows.map((row) => [
        formatDateTimeChile(row.occurred_at || row.creado_en),
        MODULE_LABEL[row.module_code] ?? row.module_code ?? '-',
        ACTION_LABELS[row.action_code] ?? row.action_code ?? '-',
        ALL_EVENT_TYPE_LABELS[row.event_type] ?? row.event_type ?? '-',
        resolveCompactEntityLabel(row),
        SEVERITY_LABEL[row.severity] ?? row.severity ?? '-',
      ]),
    })
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Auditoria central</h2>
          <p className="text-sm text-muted-foreground">
            Consulta eventos ERP y valida integridad de la cadena hash.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <ExportMenuButton
            variant="outline"
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
            disabled={rows.length === 0}
          />
          <Button variant="outline" onClick={() => void fetchEventos()} disabled={loading}>
            {loading ? 'Actualizando...' : 'Actualizar'}
          </Button>
          <Button variant="default" onClick={() => void checkIntegrity()} disabled={checkingIntegrity}>
            {checkingIntegrity ? 'Verificando...' : 'Verificar integridad'}
          </Button>
        </div>
      </header>

      {integrity ? (
        <div
          className={[
            'rounded-md border px-4 py-3 text-sm',
            integrity.is_valid
              ? 'border-emerald-300 bg-emerald-50 text-emerald-900'
              : 'border-amber-300 bg-amber-50 text-amber-900',
          ].join(' ')}
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold">
                Estado: {integrity.is_valid ? 'Valida' : 'Con inconsistencias'}
              </p>
              <p>Total eventos revisados: {integrity.total_events}</p>
              {!integrity.is_valid ? (
                <p>Eventos con inconsistencia: {(integrity.inconsistencies || []).join(', ') || '-'}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => dispatch(setAuditoriaIntegrity(null))}
              className="shrink-0 rounded p-1 text-sm leading-none opacity-60 hover:bg-black/10 hover:opacity-100"
              aria-label="Cerrar resultado de integridad"
            >
              ✕
            </button>
          </div>
        </div>
      ) : null}

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-12" onSubmit={handleSubmit}>
        {(() => {
          const meta = MODULE_METADATA[filters.module_code] ?? null
          const actionOptions = meta?.actions ?? []
          const eventTypeOptions = meta?.eventTypes ?? []
          const entityTypeOptions = meta?.entityTypes ?? []
          return (
            <>
              <label className="text-sm font-medium md:col-span-2">
                Modulo
                <SearchableSelect
                  className="mt-2"
                  value={filters.module_code}
                  onChange={(next) => updateFilter('module_code', next)}
                  options={MODULE_OPTIONS}
                  ariaLabel="Modulo"
                  placeholder="Todos los modulos"
                  emptyText="No hay modulos coincidentes"
                />
              </label>

              <label className="text-sm font-medium md:col-span-2">
                Accion
                <SearchableSelect
                  className="mt-2"
                  value={filters.action_code}
                  onChange={(next) => updateFilter('action_code', next)}
                  options={actionOptions}
                  ariaLabel="Accion"
                  placeholder={filters.module_code ? 'Todas las acciones' : 'Seleccione modulo primero'}
                  emptyText="Sin opciones para este modulo"
                  disabled={actionOptions.length === 0}
                />
              </label>

              <label className="text-sm font-medium md:col-span-3">
                Tipo de evento
                <SearchableSelect
                  className="mt-2"
                  value={filters.event_type}
                  onChange={(next) => updateFilter('event_type', next)}
                  options={eventTypeOptions}
                  ariaLabel="Tipo de evento"
                  placeholder={filters.module_code ? 'Todos los eventos' : 'Seleccione modulo primero'}
                  emptyText="Sin eventos registrados para este modulo"
                  disabled={eventTypeOptions.length === 0}
                />
              </label>

              <label className="text-sm font-medium md:col-span-2">
                Entidad
                <SearchableSelect
                  className="mt-2"
                  value={filters.entity_type}
                  onChange={(next) => updateFilter('entity_type', next)}
                  options={entityTypeOptions}
                  ariaLabel="Entidad"
                  placeholder={filters.module_code ? 'Todas' : 'Seleccione modulo primero'}
                  emptyText="Sin entidades para este modulo"
                  disabled={entityTypeOptions.length === 0}
                />
              </label>

              <label className="text-sm font-medium md:col-span-1">
                Severidad
                <SearchableSelect
                  className="mt-2"
                  value={filters.severity}
                  onChange={(next) => updateFilter('severity', next)}
                  options={SEVERITY_OPTIONS}
                  ariaLabel="Severidad"
                  placeholder="Todas"
                  emptyText="Sin opciones"
                />
              </label>

              <label className="text-sm font-medium md:col-span-1">
                Desde
                <input
                  type="date"
                  className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={filters.date_from}
                  onChange={(event) => updateFilter('date_from', event.target.value)}
                />
              </label>

              <label className="text-sm font-medium md:col-span-1">
                Hasta
                <input
                  type="date"
                  className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={filters.date_to}
                  onChange={(event) => updateFilter('date_to', event.target.value)}
                />
              </label>

              <div className="flex items-end gap-2 md:col-span-12">
                <Button type="submit" variant="default" disabled={loading}>
                  Filtrar
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    clearFilters()
                  }}
                  disabled={loading}
                >
                  Limpiar
                </Button>
              </div>
            </>
          )
        })()}
      </form>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full min-w-245 text-sm">
          <thead className="bg-muted/40 text-left">
            <tr>
              <th className="px-3 py-2">Fecha</th>
              <th className="px-3 py-2">Modulo</th>
              <th className="px-3 py-2">Accion</th>
              <th className="px-3 py-2">Evento</th>
              <th className="px-3 py-2">Entidad</th>
              <th className="px-3 py-2">Resumen</th>
              <th className="px-3 py-2">Detalle</th>
              <th className="px-3 py-2">Usuario</th>
              <th className="px-3 py-2">Severidad</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={9}>
                  {loading ? 'Cargando eventos...' : 'No hay eventos para los filtros seleccionados.'}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-border align-top">
                  <td className="px-3 py-2">{formatDateTimeChile(row.occurred_at || row.creado_en)}</td>
                  <td className="px-3 py-2 font-medium">{MODULE_LABEL[row.module_code] ?? row.module_code}</td>
                  <td className="px-3 py-2">{ACTION_LABELS[row.action_code] ?? row.action_code}</td>
                  <td className="px-3 py-2">{ALL_EVENT_TYPE_LABELS[row.event_type] ?? row.event_type}</td>
                  <td className="px-3 py-2">{resolveEntityLabel(row)}</td>
                  <td className="px-3 py-2">{row.summary || '-'}</td>
                  <td className="px-3 py-2">
                    <Link
                      to={`/auditoria/eventos/${row.id}`}
                      className="inline-flex items-center rounded-md border border-input px-2.5 py-1.5 text-xs font-medium hover:bg-muted"
                    >
                      Ver detalle
                    </Link>
                  </td>
                  <td className="px-3 py-2">{row.creado_por_email || '-'}</td>
                  <td className="px-3 py-2">{SEVERITY_LABEL[row.severity] ?? row.severity}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <TablePagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalRows={totalRows}
        pageSize={pageSize}
        onPrev={() => submitWithPage(Math.max(1, currentPage - 1))}
        onNext={() => submitWithPage(Math.min(totalPages, currentPage + 1))}
      />
    </section>
  )
}

export default AuditoriaEventosPage
