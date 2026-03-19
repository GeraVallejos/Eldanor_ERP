import { useCallback, useEffect, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { toast } from 'sonner'

import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import {
  selectAuditoriaDetalleEvento,
  selectAuditoriaDetalleStatus,
  setAuditoriaDetalleError,
  setAuditoriaDetalleEvento,
  setAuditoriaDetalleStatus,
} from '@/modules/auditoria/store/auditoriaSlice'
import Button from '@/components/ui/Button'
import MenuButton from '@/components/ui/MenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

const MODULE_LABELS = {
  AUDITORIA: 'Auditoria',
  PRESUPUESTOS: 'Presupuestos',
  PRODUCTOS: 'Productos',
  CONTACTOS: 'Contactos',
  INVENTARIO: 'Inventario',
  COMPRAS: 'Compras',
  ADMINISTRACION: 'Administracion',
  VENTAS: 'Ventas',
  FACTURACION: 'Facturacion',
  TESORERIA: 'Tesoreria',
  CONTABILIDAD: 'Contabilidad',
}

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

const SEVERITY_LABELS = {
  INFO: 'Informativo',
  WARNING: 'Advertencia',
  ERROR: 'Error',
  CRITICAL: 'Critico',
}

const EVENT_LABELS = {
  OC_CREADA: 'Orden de compra creada',
  OC_ACTUALIZADA: 'Orden de compra actualizada',
  OC_ELIMINADA: 'Orden de compra eliminada',
  DOCUMENTO_COMPRA_CREADO: 'Documento de compra creado',
  DOCUMENTO_COMPRA_ACTUALIZADO: 'Documento de compra actualizado',
  DOCUMENTO_COMPRA_ELIMINADO: 'Documento de compra eliminado',
  RECEPCION_CREADA: 'Recepcion de compra creada',
  RECEPCION_ACTUALIZADA: 'Recepcion de compra actualizada',
  RECEPCION_ELIMINADA: 'Recepcion de compra eliminada',
  COMPRA_GUIA_CONFIRMADA: 'Guia de despacho confirmada',
  COMPRA_FACTURA_CONFIRMADA_TRANSITO: 'Factura en transito confirmada',
  COMPRA_FACTURA_CONFIRMADA: 'Factura confirmada',
  COMPRA_DOCUMENTO_ANULADO: 'Documento de compra anulado',
  COMPRA_DOCUMENTO_CORREGIDO: 'Documento de compra corregido',
  COMPRA_DOCUMENTO_DUPLICADO: 'Documento de compra duplicado',
  CONTACTO_CREADO: 'Contacto creado',
  CONTACTO_ACTUALIZADO: 'Contacto actualizado',
  CONTACTO_ELIMINADO: 'Contacto eliminado',
  CLIENTE_CREADO: 'Cliente creado',
  CLIENTE_ACTUALIZADO: 'Cliente actualizado',
  CLIENTE_ELIMINADO: 'Cliente eliminado',
  PROVEEDOR_CREADO: 'Proveedor creado',
  PROVEEDOR_ACTUALIZADO: 'Proveedor actualizado',
  PROVEEDOR_ELIMINADO: 'Proveedor eliminado',
  CONTACTOS_BULK_IMPORT: 'Importacion masiva',
  INVENTARIO_MOVIMIENTO_REGISTRADO: 'Movimiento de inventario registrado',
}

const ENTITY_LABELS = {
  ORDENCOMPRA: 'Orden de compra',
  DOCUMENTOCOMPRAPROVEEDOR: 'Documento de proveedor',
  RECEPCIONCOMPRA: 'Recepcion de compra',
  DOCUMENTO_COMPRA: 'Documento de compra',
  PRESUPUESTO: 'Presupuesto',
  MOVIMIENTO_INVENTARIO: 'Movimiento de inventario',
  CONTACTO: 'Contacto',
  CLIENTE: 'Cliente',
  PROVEEDOR: 'Proveedor',
}

const DOCUMENT_TYPE_LABELS = {
  GUIA_RECEPCION: 'Guia de recepcion',
  FACTURA_COMPRA: 'Factura de compra',
}

function isUuidLike(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ''))
}

function maskTechnicalId(value) {
  const raw = String(value || '')
  if (!raw) return '-'
  if (!isUuidLike(raw)) return raw
  return `${raw.slice(0, 8)}...${raw.slice(-4)}`
}

function hasDataObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length > 0
}

function prettyJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2)
  } catch {
    return '{}'
  }
}

function getFriendlyValue(value) {
  const raw = String(value ?? '')
  if (SEVERITY_LABELS[raw]) return SEVERITY_LABELS[raw]
  if (ACTION_LABELS[raw]) return ACTION_LABELS[raw]
  if (MODULE_LABELS[raw]) return MODULE_LABELS[raw]
  if (EVENT_LABELS[raw]) return EVENT_LABELS[raw]
  if (ENTITY_LABELS[raw]) return ENTITY_LABELS[raw]
  if (DOCUMENT_TYPE_LABELS[raw]) return DOCUMENT_TYPE_LABELS[raw]
  return raw || '-'
}

function getEntityDisplay(row) {
  const payload = row?.payload || {}
  const meta = row?.meta || {}
  const base = ENTITY_LABELS[row?.entity_type] || row?.entity_type || '-'
  const tipoDocumentoCode = payload?.tipo_documento || meta?.documento_tipo
  const tipoDocumentoLabel = payload?.tipo_documento_label || DOCUMENT_TYPE_LABELS[tipoDocumentoCode] || ''
  const folio = payload?.folio || meta?.folio || ''
  const numero = payload?.numero || ''

  if (tipoDocumentoLabel || folio || numero) {
    const parts = [tipoDocumentoLabel || base]
    if (folio) parts.push(`Folio ${folio}`)
    if (numero) parts.push(`Nro ${numero}`)
    return parts.join(' · ')
  }

  if (row?.entity_id && !isUuidLike(row.entity_id)) {
    return `${base} #${row.entity_id}`
  }

  return base
}

function buildFriendlyChanges(changes) {
  if (!hasDataObject(changes)) return []

  const rows = []
  for (const [key, value] of Object.entries(changes)) {
    if (Array.isArray(value) && value.length >= 2) {
      rows.push({
        field: key,
        before: getFriendlyValue(value[0]),
        after: getFriendlyValue(value[1]),
      })
      continue
    }

    rows.push({
      field: key,
      before: '-',
      after: getFriendlyValue(value),
    })
  }

  return rows
}

function buildImportFallbackChanges(evento) {
  if (evento?.event_type !== 'CONTACTOS_BULK_IMPORT') {
    return []
  }

  const payload = evento?.payload || {}
  const hasCounters = ['created', 'updated', 'errors', 'total_rows', 'successful_rows'].some(
    (key) => payload[key] !== undefined && payload[key] !== null
  )
  if (!hasCounters) {
    return []
  }

  return [
    { field: 'Registros creados', before: '-', after: String(payload.created ?? 0) },
    { field: 'Registros actualizados', before: '-', after: String(payload.updated ?? 0) },
    { field: 'Filas con error', before: '-', after: String(payload.errors ?? 0) },
    { field: 'Filas totales', before: '-', after: String(payload.total_rows ?? 0) },
    { field: 'Filas exitosas', before: '-', after: String(payload.successful_rows ?? 0) },
  ]
}

function sanitizeEventForExport(evento) {
  const entityId = evento?.entity_id
  const safeEntityId = isUuidLike(entityId) ? null : entityId
  return {
    ...evento,
    entity_id: safeEntityId,
    entity_id_masked: entityId ? maskTechnicalId(entityId) : null,
  }
}

function downloadJsonFile(fileName, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
  URL.revokeObjectURL(url)
}

function AuditoriaEventoDetailPage() {
  const { id } = useParams()
  const dispatch = useDispatch()
  const status = useSelector(selectAuditoriaDetalleStatus)
  const evento = useSelector(selectAuditoriaDetalleEvento)

  const loadEvento = useCallback(async () => {
    dispatch(setAuditoriaDetalleStatus('loading'))
    dispatch(setAuditoriaDetalleError(null))
    try {
      const { data } = await api.get(`/auditoria/eventos/${id}/`, {
        suppressGlobalErrorToast: true,
      })
      dispatch(setAuditoriaDetalleEvento(data))
      dispatch(setAuditoriaDetalleStatus('succeeded'))
    } catch (error) {
      dispatch(setAuditoriaDetalleStatus('failed'))
      dispatch(setAuditoriaDetalleError(normalizeApiError(error, { fallback: 'No se pudo cargar el detalle del evento.' })))
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el detalle del evento.' }))
    }
  }, [dispatch, id])

  useEffect(() => {
    dispatch(setAuditoriaDetalleEvento(null))
    const timeoutId = setTimeout(() => {
      void loadEvento()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [dispatch, loadEvento])

  const friendlyChanges = useMemo(() => {
    const direct = buildFriendlyChanges(evento?.changes)
    if (direct.length > 0) {
      return direct
    }
    return buildImportFallbackChanges(evento)
  }, [evento])

  const handleExportExcel = async () => {
    if (!evento) return

    const changesRows =
      friendlyChanges.length > 0
        ? friendlyChanges.map((row) => ({
            seccion: 'Cambios',
            campo: row.field,
            valor_anterior: row.before,
            valor_nuevo: row.after,
          }))
        : [{ seccion: 'Cambios', campo: '-', valor_anterior: '-', valor_nuevo: '-' }]

    await downloadExcelFile({
      sheetName: 'DetalleAuditoria',
      fileName: `auditoria_evento_${evento.id}_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Seccion', key: 'seccion', width: 18 },
        { header: 'Campo', key: 'campo', width: 24 },
        { header: 'Valor anterior', key: 'valor_anterior', width: 36 },
        { header: 'Valor nuevo', key: 'valor_nuevo', width: 36 },
      ],
      rows: changesRows,
    })
  }

  const handleExportPdf = async () => {
    if (!evento) return

    const rows =
      friendlyChanges.length > 0
        ? friendlyChanges.map((row) => [row.field, row.before, row.after])
        : [['-', '-', '-']]

    await downloadSimpleTablePdf({
      title: `Evento auditoria ${evento.id}`,
      fileName: `auditoria_evento_${evento.id}_${getChileDateSuffix()}.pdf`,
      headers: ['Campo', 'Antes', 'Despues'],
      rows,
    })
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando evento...</p>
  }

  if (status === 'failed' || !evento) {
    return <p className="text-sm text-destructive">No se pudo cargar el evento.</p>
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Detalle de evento</h2>
          <p className="text-sm text-muted-foreground">{EVENT_LABELS[evento.event_type] || evento.event_type}</p>
        </div>

        <div className="flex items-center gap-2">
          <MenuButton variant="outline" onExportExcel={handleExportExcel} onExportPdf={handleExportPdf} />
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              downloadJsonFile(
                `auditoria_evento_${evento.id}_${getChileDateSuffix()}.json`,
                sanitizeEventForExport(evento),
              )
            }
          >
            Exportar JSON
          </Button>
          <Link to="/auditoria/eventos" className={cn(buttonVariants({ variant: 'ghost' }))}>
            Volver
          </Link>
        </div>
      </header>

      <div className="grid gap-3 md:grid-cols-2">
        <article className="rounded-md border border-border bg-card p-4 text-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Contexto</p>
          <p className="mt-2"><span className="font-medium">Fecha:</span> {formatDateTimeChile(evento.occurred_at || evento.creado_en)}</p>
          <p><span className="font-medium">Modulo:</span> {MODULE_LABELS[evento.module_code] || evento.module_code}</p>
          <p><span className="font-medium">Accion:</span> {ACTION_LABELS[evento.action_code] || evento.action_code}</p>
          <p><span className="font-medium">Severidad:</span> {SEVERITY_LABELS[evento.severity] || evento.severity}</p>
          <p><span className="font-medium">Usuario:</span> {evento.creado_por_email || '-'}</p>
        </article>

        <article className="rounded-md border border-border bg-card p-4 text-sm">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Entidad</p>
          <p className="mt-2"><span className="font-medium">Relacionado a:</span> {getEntityDisplay(evento)}</p>
          <p><span className="font-medium">Resumen:</span> {evento.summary || '-'}</p>
          <p><span className="font-medium">Id tecnico:</span> {maskTechnicalId(evento.entity_id)}</p>
        </article>
      </div>

      <article className="rounded-md border border-border bg-card p-4">
        <h3 className="text-base font-semibold">Cambios interpretados</h3>
        {friendlyChanges.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Este evento no trae cambios comparables.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-145 text-sm">
              <thead className="bg-muted/40 text-left">
                <tr>
                  <th className="px-3 py-2">Campo</th>
                  <th className="px-3 py-2">Antes</th>
                  <th className="px-3 py-2">Despues</th>
                </tr>
              </thead>
              <tbody>
                {friendlyChanges.map((row) => (
                  <tr key={`${row.field}-${row.before}-${row.after}`} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{row.field}</td>
                    <td className="px-3 py-2">{row.before}</td>
                    <td className="px-3 py-2">{row.after}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="space-y-2 rounded-md border border-border bg-card p-4">
        <h3 className="text-base font-semibold">Datos tecnicos</h3>
        <details className="rounded-md border border-border bg-muted/20 p-3 text-sm">
          <summary className="cursor-pointer font-medium">Payload (JSON)</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{prettyJson(evento.payload)}</pre>
        </details>
        <details className="rounded-md border border-border bg-muted/20 p-3 text-sm">
          <summary className="cursor-pointer font-medium">Meta (JSON)</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{prettyJson(evento.meta)}</pre>
        </details>
      </article>
    </section>
  )
}

export default AuditoriaEventoDetailPage
