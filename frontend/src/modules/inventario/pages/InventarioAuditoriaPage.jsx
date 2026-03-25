import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import MenuButton from '@/components/ui/MenuButton'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import { inventarioApi, useInventarioHistorial } from '@/modules/inventario/store'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

const DOCUMENTO_TIPO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'AJUSTE', label: 'Ajuste' },
  { value: 'TRASLADO', label: 'Traslado' },
  { value: 'GUIA_RECEPCION', label: 'Guia de recepcion' },
  { value: 'FACTURA_COMPRA', label: 'Factura de compra' },
  { value: 'VENTA_FACTURA', label: 'Factura de venta' },
  { value: 'PRESUPUESTO', label: 'Presupuesto' },
]

const TIPO_MOVIMIENTO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'ENTRADA', label: 'Entrada' },
  { value: 'SALIDA', label: 'Salida' },
]

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function formatDocumentoTipo(value) {
  const normalized = String(value || '').trim().toUpperCase()
  if (!normalized) return '-'
  const label = DOCUMENTO_TIPO_OPTIONS.find((option) => option.value === normalized)?.label
  return label || normalized.toLowerCase().replace(/_/g, ' ')
}

function prettyJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2)
  } catch {
    return '{}'
  }
}

function renderChangeValue(value) {
  if (value == null || value === '') {
    return '-'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

function buildEventRowsForExport(rows, productoById, bodegaById) {
  return rows.map((row) => ({
    fecha: formatDateTimeChile(row.occurred_at || row.creado_en),
    resumen: row.summary || '-',
    producto: productoById.get(String(row.payload?.producto_id || ''))?.nombre || row.payload?.producto_id || '-',
    bodega: bodegaById.get(String(row.payload?.bodega_id || ''))?.nombre || row.payload?.bodega_id || '-',
    documento: formatDocumentoTipo(row.payload?.documento_tipo),
    tipo: row.payload?.tipo || row.action_code || '-',
    referencia: row.payload?.documento_id || row.entity_id || '-',
  }))
}

function InventarioAuditoriaPage() {
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [loadingProductos, setLoadingProductos] = useState(false)
  const [selectedEventId, setSelectedEventId] = useState(null)
  const [filters, setFilters] = useState({
    producto_id: '',
    bodega_id: '',
    documento_tipo: '',
    tipo: '',
    referencia: '',
    desde: '',
    hasta: '',
  })
  const [submittedFilters, setSubmittedFilters] = useState({
    producto_id: '',
    bodega_id: '',
    documento_tipo: '',
    tipo: '',
    referencia: '',
    desde: '',
    hasta: '',
  })
  const [page, setPage] = useState(1)

  const {
    rows: eventos,
    pagination,
  } = useInventarioHistorial({
    filters: {
      producto_id: submittedFilters.producto_id || undefined,
      bodega_id: submittedFilters.bodega_id || undefined,
      documento_tipo: submittedFilters.documento_tipo || undefined,
      tipo: submittedFilters.tipo || undefined,
      referencia: submittedFilters.referencia || undefined,
      desde: submittedFilters.desde || undefined,
      hasta: submittedFilters.hasta || undefined,
      page,
      page_size: 20,
    },
  })

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void (async () => {
        try {
          const [productosData, bodegasData] = await Promise.all([
            searchProductosCatalog({ tipo: 'PRODUCTO' }),
            inventarioApi.getList(inventarioApi.endpoints.bodegas),
          ])
          setProductos(productosData)
          setBodegas(normalizeListResponse(bodegasData))
        } catch (error) {
          toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de auditoria de inventario.' }))
        }
      })()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  useEffect(() => {
    setSelectedEventId((prev) => {
      if (eventos.length === 0) {
        return null
      }
      const exists = eventos.some((row) => String(row.id) === String(prev))
      return exists ? prev : eventos[0].id
    })
  }, [eventos])

  const searchProductos = async (query) => {
    setLoadingProductos(true)
    try {
      const results = await searchProductosCatalog({ query, tipo: 'PRODUCTO' })
      setProductos((prev) => mergeProductosCatalog(prev, results))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron buscar productos.' }))
    } finally {
      setLoadingProductos(false)
    }
  }

  const productoOptions = useMemo(
    () =>
      productos.map((producto) => ({
        value: String(producto.id),
        label: producto.nombre || `Producto ${producto.id}`,
        keywords: `${producto.sku || ''} ${producto.tipo || ''}`,
      })),
    [productos],
  )

  const bodegaOptions = useMemo(
    () =>
      bodegas.map((bodega) => ({
        value: String(bodega.id),
        label: bodega.nombre || `Bodega ${bodega.id}`,
      })),
    [bodegas],
  )

  const productoById = useMemo(() => {
    const map = new Map()
    productos.forEach((producto) => {
      map.set(String(producto.id), producto)
    })
    return map
  }, [productos])

  const bodegaById = useMemo(() => {
    const map = new Map()
    bodegas.forEach((bodega) => {
      map.set(String(bodega.id), bodega)
    })
    return map
  }, [bodegas])

  const selectedEvent = useMemo(
    () => eventos.find((row) => String(row.id) === String(selectedEventId)) || null,
    [eventos, selectedEventId],
  )

  const exportRows = useMemo(() => buildEventRowsForExport(eventos, productoById, bodegaById), [eventos, productoById, bodegaById])

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    setPage(1)
    setSubmittedFilters({ ...filters })
  }

  const handleReset = () => {
    const clean = {
      producto_id: '',
      bodega_id: '',
      documento_tipo: '',
      tipo: '',
      referencia: '',
      desde: '',
      hasta: '',
    }
    setFilters(clean)
    setSubmittedFilters(clean)
    setPage(1)
  }

  const handleExportExcel = async () => {
    if (exportRows.length === 0) return

    await downloadExcelFile({
      sheetName: 'AuditoriaInventario',
      fileName: `auditoria_inventario_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Fecha', key: 'fecha', width: 22 },
        { header: 'Resumen', key: 'resumen', width: 40 },
        { header: 'Producto', key: 'producto', width: 28 },
        { header: 'Bodega', key: 'bodega', width: 24 },
        { header: 'Documento', key: 'documento', width: 20 },
        { header: 'Tipo', key: 'tipo', width: 16 },
        { header: 'Referencia', key: 'referencia', width: 30 },
      ],
      rows: exportRows,
    })
  }

  const handleExportPdf = async () => {
    if (exportRows.length === 0) return

    await downloadSimpleTablePdf({
      title: 'Auditoria de inventario',
      fileName: `auditoria_inventario_${getChileDateSuffix()}.pdf`,
      headers: ['Fecha', 'Resumen', 'Producto', 'Bodega', 'Documento'],
      rows: exportRows.map((row) => [row.fecha, row.resumen, row.producto, row.bodega, row.documento]),
    })
  }

  const eventChanges = selectedEvent?.changes && typeof selectedEvent.changes === 'object'
    ? Object.entries(selectedEvent.changes)
    : []

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Auditoria de inventario</h2>
          <p className="text-sm text-muted-foreground">Consulta eventos auditados del modulo, filtra por contexto operativo y revisa cambios detallados.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Ver resumen
          </Link>
          <Link to="/inventario/kardex" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Ver kardex
          </Link>
        </div>
      </div>

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4" onSubmit={handleSubmit}>
        <label className="text-sm">
          Producto
          <SearchableSelect
            className="mt-1"
            value={filters.producto_id}
            onChange={(next) => updateFilter('producto_id', next)}
            onSearchChange={(next) => { void searchProductos(next) }}
            options={productoOptions}
            ariaLabel="Producto auditoria"
            placeholder="Todos los productos"
            emptyText="No hay productos coincidentes"
            loading={loadingProductos}
          />
        </label>
        <label className="text-sm">
          Bodega
          <SearchableSelect
            className="mt-1"
            value={filters.bodega_id}
            onChange={(next) => updateFilter('bodega_id', next)}
            options={bodegaOptions}
            ariaLabel="Bodega auditoria"
            placeholder="Todas las bodegas"
            emptyText="No hay bodegas coincidentes"
          />
        </label>
        <label className="text-sm">
          Documento
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.documento_tipo}
            onChange={(event) => updateFilter('documento_tipo', event.target.value)}
          >
            {DOCUMENTO_TIPO_OPTIONS.map((option) => (
              <option key={option.value || 'all'} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Tipo de movimiento
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.tipo}
            onChange={(event) => updateFilter('tipo', event.target.value)}
          >
            {TIPO_MOVIMIENTO_OPTIONS.map((option) => (
              <option key={option.value || 'all'} value={option.value}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="text-sm md:col-span-2">
          Buscar referencia
          <input
            type="text"
            value={filters.referencia}
            onChange={(event) => updateFilter('referencia', event.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            placeholder="Documento, motivo, observacion o referencia..."
          />
        </label>
        <label className="text-sm">
          Desde
          <input
            type="date"
            value={filters.desde}
            onChange={(event) => updateFilter('desde', event.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
          />
        </label>
        <label className="text-sm">
          Hasta
          <input
            type="date"
            value={filters.hasta}
            onChange={(event) => updateFilter('hasta', event.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
          />
        </label>
        <div className="flex items-end gap-2 md:col-span-4">
          <Button type="submit">Consultar</Button>
          <Button type="button" variant="outline" onClick={handleReset}>Limpiar</Button>
          <MenuButton variant="outline" onExportExcel={handleExportExcel} onExportPdf={handleExportPdf} disabled={exportRows.length === 0} />
        </div>
      </form>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm text-muted-foreground">Eventos auditados: {pagination.count}</p>
            <h3 className="text-lg font-semibold">Historial de eventos</h3>
          </div>
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Fecha</th>
                <th className="px-3 py-2 text-left font-medium">Resumen</th>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">Bodega</th>
                <th className="px-3 py-2 text-left font-medium">Documento</th>
              </tr>
            </thead>
            <tbody>
              {eventos.length > 0 ? (
                eventos.map((row) => (
                  <tr
                    key={row.id}
                    className={cn(
                      'cursor-pointer border-t border-border',
                      String(selectedEventId) === String(row.id) ? 'bg-muted/20' : '',
                    )}
                    onClick={() => setSelectedEventId(row.id)}
                  >
                    <td className="px-3 py-2">{formatDateTimeChile(row.occurred_at || row.creado_en)}</td>
                    <td className="px-3 py-2">{row.summary || '-'}</td>
                    <td className="px-3 py-2">{productoById.get(String(row.payload?.producto_id || ''))?.nombre || row.payload?.producto_id || '-'}</td>
                    <td className="px-3 py-2">{bodegaById.get(String(row.payload?.bodega_id || ''))?.nombre || row.payload?.bodega_id || '-'}</td>
                    <td className="px-3 py-2">{formatDocumentoTipo(row.payload?.documento_tipo)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={5}>No hay eventos para los filtros seleccionados.</td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <p className="text-xs text-muted-foreground">Pagina actual: {page}</p>
            <div className="flex gap-2">
              <Button type="button" size="sm" variant="outline" disabled={!pagination.previous || page <= 1} onClick={() => setPage((prev) => Math.max(prev - 1, 1))}>
                Anterior
              </Button>
              <Button type="button" size="sm" variant="outline" disabled={!pagination.next} onClick={() => setPage((prev) => prev + 1)}>
                Siguiente
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <article className="rounded-md border border-border bg-card p-4">
            <h3 className="text-lg font-semibold">Detalle del evento</h3>
            {selectedEvent ? (
              <div className="mt-3 space-y-2 text-sm">
                <p><span className="font-medium">Fecha:</span> {formatDateTimeChile(selectedEvent.occurred_at || selectedEvent.creado_en)}</p>
                <p><span className="font-medium">Resumen:</span> {selectedEvent.summary || '-'}</p>
                <p><span className="font-medium">Accion:</span> {selectedEvent.action_code || '-'}</p>
                <p><span className="font-medium">Evento:</span> {selectedEvent.event_type || '-'}</p>
                <p><span className="font-medium">Entidad:</span> {selectedEvent.entity_type || '-'} / {selectedEvent.entity_id || '-'}</p>
                <p><span className="font-medium">Documento:</span> {formatDocumentoTipo(selectedEvent.payload?.documento_tipo)}</p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">Selecciona un evento para revisar su detalle.</p>
            )}
          </article>

          <article className="rounded-md border border-border bg-card p-4">
            <h3 className="text-lg font-semibold">Cambios</h3>
            {eventChanges.length > 0 ? (
              <div className="mt-3 space-y-2">
                {eventChanges.map(([field, change]) => (
                  <div key={field} className="rounded-md border border-border bg-muted/20 px-3 py-2 text-sm">
                    <p className="font-medium">{field}</p>
                    <p className="text-muted-foreground">
                      {Array.isArray(change)
                        ? `${renderChangeValue(change[0])} -> ${renderChangeValue(change[1])}`
                        : renderChangeValue(change)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">El evento seleccionado no trae cambios comparables.</p>
            )}
          </article>

          <article className="space-y-2 rounded-md border border-border bg-card p-4">
            <h3 className="text-lg font-semibold">Datos tecnicos</h3>
            <details className="rounded-md border border-border bg-muted/20 p-3 text-sm">
              <summary className="cursor-pointer font-medium">Payload (JSON)</summary>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{prettyJson(selectedEvent?.payload)}</pre>
            </details>
            <details className="rounded-md border border-border bg-muted/20 p-3 text-sm">
              <summary className="cursor-pointer font-medium">Meta (JSON)</summary>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{prettyJson(selectedEvent?.meta)}</pre>
            </details>
          </article>
        </div>
      </div>
    </section>
  )
}

export default InventarioAuditoriaPage
