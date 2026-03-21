import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import MenuButton from '@/components/ui/MenuButton'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { formatMoney } from '@/modules/ventas/utils'

function formatDateRangeLabel(from, to) {
  if (from && to) return `${formatDateChile(from)} a ${formatDateChile(to)}`
  if (from) return `Desde ${formatDateChile(from)}`
  if (to) return `Hasta ${formatDateChile(to)}`
  return 'Periodo abierto'
}

function VentasReportesPage() {
  const [analytics, setAnalytics] = useState(null)
  const [filters, setFilters] = useState({
    fecha_desde: '',
    fecha_hasta: '',
    cliente: '',
    estado: 'ALL',
    cartera: 'ALL',
    agrupacion: 'mensual',
  })

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void api
        .get('/facturas-venta/analytics/', {
          params: {
            fecha_desde: filters.fecha_desde || undefined,
            fecha_hasta: filters.fecha_hasta || undefined,
            cliente: filters.cliente || undefined,
            estado: filters.estado,
            cartera: filters.cartera,
            agrupacion: filters.agrupacion,
          },
          suppressGlobalErrorToast: true,
        })
        .then((response) => setAnalytics(response.data))
        .catch((error) => {
          toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los reportes de ventas.' }))
        })
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [filters])

  const clienteOptions = useMemo(
    () =>
      Array.from(new Set((analytics?.detail || []).map((row) => row.cliente_nombre).filter(Boolean))).map((value) => ({
        value,
        label: value,
      })),
    [analytics?.detail],
  )

  const suffix = getChileDateSuffix()
  const clienteActivo =
    clienteOptions.find((option) => option.value === String(filters.cliente || ''))?.label || 'Todos'

  const exportExcel = async () => {
    const rows = analytics?.detail || []
    if (rows.length === 0) return
    await downloadExcelFile({
      sheetName: 'ReporteVentas',
      fileName: `reporte_ventas_${suffix}.xlsx`,
      columns: [
        { header: 'Numero', key: 'numero', width: 18 },
        { header: 'Cliente', key: 'cliente_nombre', width: 30 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 18 },
        { header: 'Fecha vencimiento', key: 'fecha_vencimiento', width: 18 },
        { header: 'Estado', key: 'estado', width: 16 },
        { header: 'Total', key: 'total', width: 18 },
        { header: 'Agrupacion', key: 'agrupacion', width: 18 },
      ],
      rows: rows.map((row) => ({
        ...row,
        fecha_emision: formatDateChile(row.fecha_emision),
        fecha_vencimiento: row.fecha_vencimiento ? formatDateChile(row.fecha_vencimiento) : '-',
        agrupacion: analytics?.filters?.agrupacion || filters.agrupacion,
      })),
    })
  }

  const exportPdf = async () => {
    const rows = analytics?.detail || []
    if (rows.length === 0) return
    await downloadSimpleTablePdf({
      title: 'Reporte de ventas',
      fileName: `reporte_ventas_${suffix}.pdf`,
      headers: ['Numero', 'Cliente', 'Emision', 'Vencimiento', 'Estado', 'Total'],
      rows: rows.map((row) => [
        row.numero || '-',
        row.cliente_nombre || '-',
        formatDateChile(row.fecha_emision),
        row.fecha_vencimiento ? formatDateChile(row.fecha_vencimiento) : '-',
        row.estado || '-',
        formatMoney(row.total || 0),
      ]),
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Reportes de ventas</h2>
          <p className="text-sm text-muted-foreground">
            Analiza facturacion y cartera con datos analiticos servidos desde backend.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <Link to="/ventas/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver resumen
          </Link>
          <Link to="/ventas/facturas" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver facturas
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
          Cliente
          <SearchableSelect className="mt-1" value={filters.cliente} onChange={(next) => setFilters((prev) => ({ ...prev, cliente: next }))} options={clienteOptions} ariaLabel="Cliente" placeholder="Buscar cliente..." emptyText="No hay clientes coincidentes" />
        </label>
        <label className="text-sm">
          Agrupacion temporal
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.agrupacion} onChange={(event) => setFilters((prev) => ({ ...prev, agrupacion: event.target.value }))}>
            <option value="mensual">Mensual</option>
            <option value="semanal">Semanal</option>
          </select>
        </label>
        <label className="text-sm">
          Estado
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.estado} onChange={(event) => setFilters((prev) => ({ ...prev, estado: event.target.value }))}>
            <option value="ALL">Todos</option>
            <option value="BORRADOR">Borrador</option>
            <option value="EMITIDA">Emitida</option>
            <option value="ANULADA">Anulada</option>
          </select>
        </label>
        <label className="text-sm">
          Foco de cartera
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.cartera} onChange={(event) => setFilters((prev) => ({ ...prev, cartera: event.target.value }))}>
            <option value="ALL">Todas</option>
            <option value="VENCIDAS">Solo vencidas</option>
            <option value="POR_VENCER_7_DIAS">Por vencer en 7 dias</option>
            <option value="BORRADORES">Solo borradores</option>
          </select>
        </label>
      </div>

      <div className="rounded-md border border-dashed border-border bg-card/60 p-4 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">Contexto del analisis</p>
        <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <p>Periodo: <span className="font-medium text-foreground">{formatDateRangeLabel(filters.fecha_desde, filters.fecha_hasta)}</span></p>
          <p>Cliente: <span className="font-medium text-foreground">{clienteActivo}</span></p>
          <p>Estado: <span className="font-medium text-foreground">{filters.estado === 'ALL' ? 'Todos los estados' : filters.estado}</span></p>
          <p>Cartera: <span className="font-medium text-foreground">{filters.cartera === 'ALL' ? 'Todas' : filters.cartera}</span></p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted-foreground">Reporte comercial</p>
              <h3 className="mt-1 text-lg font-semibold">Facturacion</h3>
            </div>
            <MenuButton variant="outline" onExportExcel={exportExcel} onExportPdf={exportPdf} disabled={!analytics?.detail?.length} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Facturacion total</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(analytics?.metrics?.facturacion_total || 0)}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto emitido</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(analytics?.metrics?.monto_emitido || 0)}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <p>Facturas: <span className="font-medium">{analytics?.metrics?.total_facturas || 0}</span></p>
            <p>Emitidas / Borradores / Anuladas: <span className="font-medium">{analytics?.metrics?.emitidas || 0} / {analytics?.metrics?.borradores || 0} / {analytics?.metrics?.anuladas || 0}</span></p>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top clientes por monto</p>
            <div className="mt-2 space-y-1 text-sm">
              {(analytics?.top_clientes || []).length > 0 ? (analytics?.top_clientes || []).map((row) => (
                <p key={row.cliente_id}>{row.nombre}: <span className="font-medium">{formatMoney(row.total)}</span></p>
              )) : <p className="text-muted-foreground">Sin datos para ranking.</p>}
            </div>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Top productos vendidos</p>
            <div className="mt-2 space-y-1 text-sm">
              {(analytics?.top_productos || []).length > 0 ? (analytics?.top_productos || []).map((row, index) => (
                <p key={`${row.producto_id}-${index}`}>{row.nombre}: <span className="font-medium">{formatMoney(row.monto)}</span> / {row.cantidad}</p>
              )) : <p className="text-muted-foreground">Sin datos de items para ranking.</p>}
            </div>
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted-foreground">Reporte de cartera</p>
              <h3 className="mt-1 text-lg font-semibold">Cobranza comercial</h3>
            </div>
            <MenuButton variant="outline" onExportExcel={exportExcel} onExportPdf={exportPdf} disabled={!analytics?.detail?.length} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto vencido</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(analytics?.metrics?.monto_vencido || 0)}</p>
            </div>
            <div className="rounded-md border border-border p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto por vencer</p>
              <p className="mt-1 text-lg font-semibold">{formatMoney(analytics?.metrics?.monto_por_vencer || 0)}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            <p>Vencidas: <span className="font-medium">{analytics?.metrics?.vencidas || 0}</span></p>
            <p>Por vencer: <span className="font-medium">{analytics?.metrics?.por_vencer || 0}</span></p>
          </div>
          <div className="mt-4 rounded-md border border-border p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Documentos vencidos a vigilar</p>
            <div className="mt-2 space-y-1 text-sm">
              {(analytics?.documentos_vencidos || []).length > 0 ? (analytics?.documentos_vencidos || []).map((row) => (
                <p key={row.id}>{row.numero} / {row.cliente_nombre}: <span className="font-medium">{formatMoney(row.total)}</span></p>
              )) : <p className="text-muted-foreground">Sin documentos vencidos para este filtro.</p>}
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-border bg-card p-4">
          <div className="mb-3">
            <p className="text-sm text-muted-foreground">Serie comercial</p>
            <h3 className="text-lg font-semibold">Tendencia de facturacion</h3>
          </div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Tendencia {filters.agrupacion === 'semanal' ? 'semanal' : 'mensual'}</p>
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
                {(analytics?.series || []).length > 0 ? (analytics?.series || []).map((row, index) => (
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

        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm text-muted-foreground">Detalle exportable</p>
            <h3 className="text-lg font-semibold">Facturas filtradas</h3>
          </div>
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Numero</th>
                <th className="px-3 py-2 text-left font-medium">Cliente</th>
                <th className="px-3 py-2 text-left font-medium">Emision</th>
                <th className="px-3 py-2 text-left font-medium">Vencimiento</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
                <th className="px-3 py-2 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {(analytics?.detail || []).length > 0 ? (analytics?.detail || []).map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-3 py-2">{row.numero || '-'}</td>
                  <td className="px-3 py-2">{row.cliente_nombre || '-'}</td>
                  <td className="px-3 py-2">{formatDateChile(row.fecha_emision)}</td>
                  <td className="px-3 py-2">{row.fecha_vencimiento ? formatDateChile(row.fecha_vencimiento) : '-'}</td>
                  <td className="px-3 py-2">{row.estado || '-'}</td>
                  <td className="px-3 py-2 text-right">{formatMoney(row.total || 0)}</td>
                </tr>
              )) : (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={6}>Sin facturas para el filtro aplicado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default VentasReportesPage
