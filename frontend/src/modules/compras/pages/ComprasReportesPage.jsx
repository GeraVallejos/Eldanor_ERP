import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import MenuButton from '@/components/ui/MenuButton'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function formatDateRangeLabel(from, to) {
  if (from && to) return `${formatDateChile(from)} a ${formatDateChile(to)}`
  if (from) return `Desde ${formatDateChile(from)}`
  if (to) return `Hasta ${formatDateChile(to)}`
  return 'Periodo abierto'
}

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function ComprasReportesPage() {
  const [analytics, setAnalytics] = useState(null)
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [filters, setFilters] = useState({
    fecha_desde: '',
    fecha_hasta: '',
    proveedor_id: '',
    estado_orden: 'ALL',
    estado_documento: 'ALL',
    tipo_documento: 'ALL',
    agrupacion: 'mensual',
  })

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void Promise.all([
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
      ])
        .then(([proveedoresResponse, contactosResponse]) => {
          setProveedores(normalizeListResponse(proveedoresResponse.data))
          setContactos(normalizeListResponse(contactosResponse.data))
        })
        .catch((error) => {
          toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de compras.' }))
        })
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void Promise.all([
        api.get('/ordenes-compra/analytics/', {
          params: {
            fecha_desde: filters.fecha_desde || undefined,
            fecha_hasta: filters.fecha_hasta || undefined,
            proveedor_id: filters.proveedor_id || undefined,
            estado: filters.estado_orden,
            agrupacion: filters.agrupacion,
          },
          suppressGlobalErrorToast: true,
        }),
        api.get('/documentos-compra/analytics/', {
          params: {
            fecha_desde: filters.fecha_desde || undefined,
            fecha_hasta: filters.fecha_hasta || undefined,
            proveedor_id: filters.proveedor_id || undefined,
            estado: filters.estado_documento,
            tipo_documento: filters.tipo_documento,
            agrupacion: filters.agrupacion,
          },
          suppressGlobalErrorToast: true,
        }),
      ])
        .then(([ordenesResponse, documentosResponse]) => {
          setAnalytics({
            ordenes: ordenesResponse.data,
            documentos: documentosResponse.data,
          })
        })
        .catch((error) => {
          toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los reportes de compras.' }))
        })
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [filters])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((item) => map.set(String(item.id), item))
    return map
  }, [contactos])

  const proveedorOptions = useMemo(
    () =>
      proveedores.map((proveedor) => {
        const contacto = contactoById.get(String(proveedor.contacto))
        return {
          value: String(proveedor.id),
          label: contacto?.nombre || `Proveedor ${proveedor.id}`,
        }
      }),
    [proveedores, contactoById],
  )

  const suffix = getChileDateSuffix()
  const ordenesAnalytics = analytics?.ordenes
  const documentosAnalytics = analytics?.documentos
  const proveedorActivo =
    proveedorOptions.find((option) => option.value === String(filters.proveedor_id || ''))?.label || 'Todos'

  const exportOrdenesExcel = async () => {
    const rows = ordenesAnalytics?.detail || []
    if (rows.length === 0) return
    await downloadExcelFile({
      sheetName: 'ReporteOrdenesCompra',
      fileName: `reporte_ordenes_compra_${suffix}.xlsx`,
      columns: [
        { header: 'Numero', key: 'numero', width: 18 },
        { header: 'Proveedor', key: 'proveedor_nombre', width: 30 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 18 },
        { header: 'Estado', key: 'estado', width: 18 },
        { header: 'Total', key: 'total', width: 18 },
        { header: 'Agrupacion', key: 'agrupacion', width: 18 },
      ],
      rows: rows.map((row) => ({
        ...row,
        fecha_emision: formatDateChile(row.fecha_emision),
        agrupacion: ordenesAnalytics?.filters?.agrupacion || filters.agrupacion,
      })),
    })
  }

  const exportOrdenesPdf = async () => {
    const rows = ordenesAnalytics?.detail || []
    if (rows.length === 0) return
    await downloadSimpleTablePdf({
      title: 'Reporte de ordenes de compra',
      fileName: `reporte_ordenes_compra_${suffix}.pdf`,
      headers: ['Numero', 'Proveedor', 'Fecha', 'Estado', 'Total'],
      rows: rows.map((row) => [
        row.numero || '-',
        row.proveedor_nombre || '-',
        formatDateChile(row.fecha_emision),
        row.estado || '-',
        formatMoney(row.total || 0),
      ]),
    })
  }

  const exportDocumentosExcel = async () => {
    const rows = documentosAnalytics?.detail || []
    if (rows.length === 0) return
    await downloadExcelFile({
      sheetName: 'ReporteDocumentosCompra',
      fileName: `reporte_documentos_compra_${suffix}.xlsx`,
      columns: [
        { header: 'Tipo', key: 'tipo_documento', width: 24 },
        { header: 'Folio', key: 'folio', width: 18 },
        { header: 'Proveedor', key: 'proveedor_nombre', width: 30 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 18 },
        { header: 'Estado', key: 'estado', width: 18 },
        { header: 'Total', key: 'total', width: 18 },
        { header: 'Agrupacion', key: 'agrupacion', width: 18 },
      ],
      rows: rows.map((row) => ({
        ...row,
        fecha_emision: formatDateChile(row.fecha_emision),
        agrupacion: documentosAnalytics?.filters?.agrupacion || filters.agrupacion,
      })),
    })
  }

  const exportDocumentosPdf = async () => {
    const rows = documentosAnalytics?.detail || []
    if (rows.length === 0) return
    await downloadSimpleTablePdf({
      title: 'Reporte documental de compras',
      fileName: `reporte_documentos_compra_${suffix}.pdf`,
      headers: ['Tipo', 'Folio', 'Proveedor', 'Fecha', 'Estado', 'Total'],
      rows: rows.map((row) => [
        row.tipo_documento || '-',
        row.folio || '-',
        row.proveedor_nombre || '-',
        formatDateChile(row.fecha_emision),
        row.estado || '-',
        formatMoney(row.total || 0),
      ]),
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Reportes de compras</h2>
          <p className="text-sm text-muted-foreground">
            Analiza abastecimiento y documentos con filtros, tendencias y rankings calculados desde backend.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <Link to="/compras/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver resumen
          </Link>
          <Link to="/compras/ordenes" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver ordenes
          </Link>
          <Link to="/compras/documentos" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver documentos
          </Link>
        </div>
      </div>

      <div className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="text-sm">
          Fecha desde
          <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.fecha_desde} onChange={(event) => setFilters((prev) => ({ ...prev, fecha_desde: event.target.value }))} />
        </label>
        <label className="text-sm">
          Fecha hasta
          <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.fecha_hasta} onChange={(event) => setFilters((prev) => ({ ...prev, fecha_hasta: event.target.value }))} />
        </label>
        <label className="text-sm">
          Proveedor
          <SearchableSelect className="mt-1" value={filters.proveedor_id} onChange={(next) => setFilters((prev) => ({ ...prev, proveedor_id: next }))} options={proveedorOptions} ariaLabel="Proveedor" placeholder="Buscar proveedor..." emptyText="No hay proveedores coincidentes" />
        </label>
        <label className="text-sm">
          Agrupacion temporal
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.agrupacion} onChange={(event) => setFilters((prev) => ({ ...prev, agrupacion: event.target.value }))}>
            <option value="mensual">Mensual</option>
            <option value="semanal">Semanal</option>
          </select>
        </label>
        <label className="text-sm">
          Estado de orden
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.estado_orden} onChange={(event) => setFilters((prev) => ({ ...prev, estado_orden: event.target.value }))}>
            <option value="ALL">Todos</option>
            <option value="BORRADOR">Borrador</option>
            <option value="ENVIADA">Enviada</option>
            <option value="PARCIAL">Parcial</option>
            <option value="RECIBIDA">Recibida</option>
            <option value="CANCELADA">Cancelada</option>
          </select>
        </label>
        <label className="text-sm">
          Estado documental
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.estado_documento} onChange={(event) => setFilters((prev) => ({ ...prev, estado_documento: event.target.value }))}>
            <option value="ALL">Todos</option>
            <option value="BORRADOR">Borrador</option>
            <option value="CONFIRMADO">Confirmado</option>
            <option value="ANULADO">Anulado</option>
          </select>
        </label>
        <label className="text-sm">
          Tipo documental
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.tipo_documento} onChange={(event) => setFilters((prev) => ({ ...prev, tipo_documento: event.target.value }))}>
            <option value="ALL">Todos</option>
            <option value="FACTURA_COMPRA">Facturas</option>
            <option value="GUIA_RECEPCION">Guias</option>
            <option value="BOLETA_COMPRA">Boletas</option>
          </select>
        </label>
      </div>

      <div className="rounded-md border border-dashed border-border bg-card/60 p-4 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">Contexto del analisis</p>
        <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <p>Periodo: <span className="font-medium text-foreground">{formatDateRangeLabel(filters.fecha_desde, filters.fecha_hasta)}</span></p>
          <p>Proveedor: <span className="font-medium text-foreground">{proveedorActivo}</span></p>
          <p>Ordenes: <span className="font-medium text-foreground">{filters.estado_orden === 'ALL' ? 'Todos los estados' : filters.estado_orden}</span></p>
          <p>Documentos: <span className="font-medium text-foreground">{filters.tipo_documento === 'ALL' ? 'Todos los tipos' : filters.tipo_documento}</span></p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted-foreground">Reporte operativo</p>
              <h3 className="mt-1 text-lg font-semibold">Ordenes de compra</h3>
            </div>
            <MenuButton variant="outline" onExportExcel={exportOrdenesExcel} onExportPdf={exportOrdenesPdf} disabled={!ordenesAnalytics?.detail?.length} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto comprometido</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(ordenesAnalytics?.metrics?.monto_comprometido || 0)}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Pendientes de recepcion</p>
              <p className="mt-1 text-lg font-semibold">{ordenesAnalytics?.metrics?.pendientes_recepcion || 0}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <p>Total ordenes: <span className="font-medium">{ordenesAnalytics?.metrics?.total_ordenes || 0}</span></p>
            <p>Enviadas / Parciales / Recibidas: <span className="font-medium">{ordenesAnalytics?.metrics?.enviadas || 0} / {ordenesAnalytics?.metrics?.parciales || 0} / {ordenesAnalytics?.metrics?.recibidas || 0}</span></p>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top proveedores por monto</p>
            <div className="mt-2 space-y-1 text-sm">
              {(ordenesAnalytics?.top_proveedores || []).length > 0 ? (ordenesAnalytics?.top_proveedores || []).map((row) => (
                <p key={row.proveedor_id}>{row.nombre}: <span className="font-medium">{formatMoney(row.total)}</span></p>
              )) : <p className="text-muted-foreground">Sin datos para ranking.</p>}
            </div>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top productos comprados</p>
            <div className="mt-2 space-y-1 text-sm">
              {(ordenesAnalytics?.top_productos || []).length > 0 ? (ordenesAnalytics?.top_productos || []).map((row, index) => (
                <p key={`${row.producto_id}-${index}`}>{row.nombre}: <span className="font-medium">{formatMoney(row.monto)}</span> / {row.cantidad}</p>
              )) : <p className="text-muted-foreground">Sin datos de items para ranking.</p>}
            </div>
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted-foreground">Reporte documental</p>
              <h3 className="mt-1 text-lg font-semibold">Documentos de compra</h3>
            </div>
            <MenuButton variant="outline" onExportExcel={exportDocumentosExcel} onExportPdf={exportDocumentosPdf} disabled={!documentosAnalytics?.detail?.length} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto documental</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(documentosAnalytics?.metrics?.monto_documental || 0)}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto confirmado</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(documentosAnalytics?.metrics?.monto_confirmado || 0)}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <p>Documentos de compra: <span className="font-medium">{documentosAnalytics?.metrics?.total_documentos || 0}</span></p>
            <p>Pendientes documentales: <span className="font-medium">{documentosAnalytics?.metrics?.pendientes_documentales || 0}</span></p>
            <p>Facturas / Guias / Boletas: <span className="font-medium">{documentosAnalytics?.metrics?.facturas || 0} / {documentosAnalytics?.metrics?.guias || 0} / {documentosAnalytics?.metrics?.boletas || 0}</span></p>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top proveedores por monto documental</p>
            <div className="mt-2 space-y-1 text-sm">
              {(documentosAnalytics?.top_proveedores || []).length > 0 ? (documentosAnalytics?.top_proveedores || []).map((row) => (
                <p key={row.proveedor_id}>{row.nombre}: <span className="font-medium">{formatMoney(row.total)}</span></p>
              )) : <p className="text-muted-foreground">Sin datos para ranking.</p>}
            </div>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top productos documentados</p>
            <div className="mt-2 space-y-1 text-sm">
              {(documentosAnalytics?.top_productos || []).length > 0 ? (documentosAnalytics?.top_productos || []).map((row, index) => (
                <p key={`${row.producto_id}-${index}`}>{row.nombre}: <span className="font-medium">{formatMoney(row.monto)}</span> / {row.cantidad}</p>
              )) : <p className="text-muted-foreground">Sin datos de items para ranking.</p>}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-border bg-card p-4">
          <div className="mb-3">
            <p className="text-sm text-muted-foreground">Serie operativa</p>
            <h3 className="text-lg font-semibold">Tendencia de ordenes</h3>
          </div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Tendencia {filters.agrupacion === 'semanal' ? 'semanal' : 'mensual'} de ordenes</p>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Periodo</th>
                  <th className="px-3 py-2 text-left font-medium">Cantidad</th>
                  <th className="px-3 py-2 text-right font-medium">Monto</th>
                </tr>
              </thead>
              <tbody>
                {(ordenesAnalytics?.series || []).length > 0 ? (ordenesAnalytics?.series || []).map((row, index) => (
                  <tr key={`${row.periodo}-${index}`} className="border-t border-border">
                    <td className="px-3 py-2">{row.periodo || '-'}</td>
                    <td className="px-3 py-2">{row.cantidad}</td>
                    <td className="px-3 py-2 text-right">{formatMoney(row.monto)}</td>
                  </tr>
                )) : (
                  <tr>
                    <td className="px-3 py-3 text-muted-foreground" colSpan={3}>Sin datos para tendencia.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <div className="mb-3">
            <p className="text-sm text-muted-foreground">Serie documental</p>
            <h3 className="text-lg font-semibold">Tendencia de documentos</h3>
          </div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Tendencia {filters.agrupacion === 'semanal' ? 'semanal' : 'mensual'} documental</p>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Periodo</th>
                  <th className="px-3 py-2 text-left font-medium">Cantidad</th>
                  <th className="px-3 py-2 text-right font-medium">Monto</th>
                </tr>
              </thead>
              <tbody>
                {(documentosAnalytics?.series || []).length > 0 ? (documentosAnalytics?.series || []).map((row, index) => (
                  <tr key={`${row.periodo}-${index}`} className="border-t border-border">
                    <td className="px-3 py-2">{row.periodo || '-'}</td>
                    <td className="px-3 py-2">{row.cantidad}</td>
                    <td className="px-3 py-2 text-right">{formatMoney(row.monto)}</td>
                  </tr>
                )) : (
                  <tr>
                    <td className="px-3 py-3 text-muted-foreground" colSpan={3}>Sin datos para tendencia.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm text-muted-foreground">Detalle exportable</p>
            <h3 className="text-lg font-semibold">Ordenes filtradas</h3>
          </div>
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Numero</th>
                <th className="px-3 py-2 text-left font-medium">Proveedor</th>
                <th className="px-3 py-2 text-left font-medium">Fecha</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
                <th className="px-3 py-2 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {(ordenesAnalytics?.detail || []).length > 0 ? (
                (ordenesAnalytics?.detail || []).map((row) => (
                  <tr key={row.id} className="border-t border-border">
                    <td className="px-3 py-2">{row.numero || '-'}</td>
                    <td className="px-3 py-2">{row.proveedor_nombre || '-'}</td>
                    <td className="px-3 py-2">{formatDateChile(row.fecha_emision)}</td>
                    <td className="px-3 py-2">{row.estado || '-'}</td>
                    <td className="px-3 py-2 text-right">{formatMoney(row.total || 0)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={5}>Sin ordenes para el filtro aplicado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm text-muted-foreground">Detalle exportable</p>
            <h3 className="text-lg font-semibold">Documentos filtrados</h3>
          </div>
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Tipo</th>
                <th className="px-3 py-2 text-left font-medium">Folio</th>
                <th className="px-3 py-2 text-left font-medium">Proveedor</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
                <th className="px-3 py-2 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {(documentosAnalytics?.detail || []).length > 0 ? (
                (documentosAnalytics?.detail || []).map((row) => (
                  <tr key={row.id} className="border-t border-border">
                    <td className="px-3 py-2">{row.tipo_documento || '-'}</td>
                    <td className="px-3 py-2">{row.folio || '-'}</td>
                    <td className="px-3 py-2">{row.proveedor_nombre || '-'}</td>
                    <td className="px-3 py-2">{row.estado || '-'}</td>
                    <td className="px-3 py-2 text-right">{formatMoney(row.total || 0)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={5}>Sin documentos para el filtro aplicado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default ComprasReportesPage
