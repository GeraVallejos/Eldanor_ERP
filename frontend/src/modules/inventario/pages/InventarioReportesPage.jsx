import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import MenuButton from '@/components/ui/MenuButton'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { getProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
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

function formatNumber(value) {
  return formatSmartNumber(value, { maximumFractionDigits: 2 })
}

function formatCurrency(value) {
  return formatCurrencyCLP(value)
}

function formatInventoryContext({ groupBy, producto, bodega, onlyWithStock }) {
  return [
    `Vista: ${groupBy === 'bodega' ? 'Por bodega' : 'Por producto'}`,
    `Producto: ${producto || 'Todos'}`,
    `Bodega: ${bodega || 'Todas'}`,
    `Solo con stock: ${onlyWithStock ? 'Si' : 'No'}`,
  ]
}

function InventarioReportesPage() {
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [filters, setFilters] = useState({
    group_by: 'producto',
    producto_id: '',
    bodega_id: '',
  })
  const [onlyWithStock, setOnlyWithStock] = useState(true)

  const loadCatalogs = async () => {
    try {
      const [productosData, { data: bodegasData }] = await Promise.all([
        getProductosCatalog(),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de reportes.' }))
    }
  }

  const loadAnalytics = async (nextFilters, nextOnlyWithStock = onlyWithStock) => {
    try {
      const { data } = await api.get('/stocks/analytics/', {
        params: {
          ...nextFilters,
          only_with_stock: nextOnlyWithStock,
        },
        suppressGlobalErrorToast: true,
      })
      setAnalytics(data)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el reporte de inventario.' }))
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadCatalogs()
      void loadAnalytics({
        group_by: 'producto',
        producto_id: '',
        bodega_id: '',
      }, true)
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
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

  const productoById = useMemo(() => {
    const map = new Map()
    productos.forEach((producto) => {
      map.set(String(producto.id), producto)
    })
    return map
  }, [productos])

  const bodegaOptions = useMemo(
    () =>
      bodegas.map((bodega) => ({
        value: String(bodega.id),
        label: bodega.nombre || `Bodega ${bodega.id}`,
      })),
    [bodegas],
  )

  const bodegaById = useMemo(() => {
    const map = new Map()
    bodegas.forEach((bodega) => {
      map.set(String(bodega.id), bodega)
    })
    return map
  }, [bodegas])

  const onSubmit = async (event) => {
    event.preventDefault()
    await loadAnalytics(filters)
  }

  const getTodaySuffix = () => getChileDateSuffix()

  const detalleRows = useMemo(() => {
    const rows = Array.isArray(analytics?.detalle) ? analytics.detalle : []

    if (filters.group_by === 'bodega') {
      return rows.map((row) => ({
        groupLabel: row.bodega__nombre || '-',
        stockTotal: Number(row.stock_total || 0),
        reservadoTotal: Number(row.reservado_total || 0),
        disponibleTotal: Number(row.disponible_total || 0),
        valorTotal: Number(row.valor_total || 0),
      }))
    }

    return rows.map((row) => {
      const productoId = String(row.producto_id || '')
      const producto = productoById.get(productoId)
      return {
        groupLabel: row.producto__nombre || producto?.nombre || '-',
        categoria: row.producto__categoria__nombre || '-',
        sku: producto?.sku || '-',
        tipo: producto?.tipo || '-',
        stockTotal: Number(row.stock_total || 0),
        reservadoTotal: Number(row.reservado_total || 0),
        disponibleTotal: Number(row.disponible_total || 0),
        valorTotal: Number(row.valor_total || 0),
      }
    })
  }, [analytics, filters.group_by, productoById])

  const visibleRows = detalleRows

  const handleExportExcel = async () => {
    const rows = visibleRows
    if (rows.length === 0) {
      return
    }

    const filtroProductoLabel = filters.producto_id
      ? productoById.get(String(filters.producto_id))?.nombre || String(filters.producto_id)
      : 'Todos'
    const filtroBodegaLabel = filters.bodega_id
      ? bodegaById.get(String(filters.bodega_id))?.nombre || String(filters.bodega_id)
      : 'Todas'
    const valorTotalGeneral = Number(analytics?.totales?.valor_total || 0)
    const now = new Date()

    await downloadExcelFile({
      sheetName: 'ResumenInventario',
      fileName: `resumen_inventario_${getTodaySuffix()}.xlsx`,
      columns:
        filters.group_by === 'bodega'
          ? [
              { header: 'Bodega', key: 'grupo', width: 30 },
              { header: 'Stock total', key: 'stock_total', width: 14 },
              { header: 'Stock reservado', key: 'reservado_total', width: 16 },
              { header: 'Stock disponible', key: 'disponible_total', width: 16 },
              { header: 'Valor total', key: 'valor_total', width: 16 },
              { header: 'Costo promedio', key: 'costo_promedio', width: 16 },
              { header: '% valor inventario', key: 'participacion_valor_pct', width: 18 },
              { header: 'Agrupacion', key: 'ctx_group_by', width: 14 },
              { header: 'Filtro producto', key: 'ctx_producto', width: 24 },
              { header: 'Filtro bodega', key: 'ctx_bodega', width: 24 },
              { header: 'Solo con stock', key: 'ctx_only_with_stock', width: 16 },
              { header: 'Exportado en', key: 'ctx_exportado_en', width: 22 },
            ]
          : [
              { header: 'Producto', key: 'grupo', width: 30 },
              { header: 'Categoria', key: 'categoria', width: 22 },
              { header: 'SKU', key: 'sku', width: 18 },
              { header: 'Tipo', key: 'tipo', width: 16 },
              { header: 'Stock total', key: 'stock_total', width: 14 },
              { header: 'Stock reservado', key: 'reservado_total', width: 16 },
              { header: 'Stock disponible', key: 'disponible_total', width: 16 },
              { header: 'Valor total', key: 'valor_total', width: 16 },
              { header: 'Costo promedio', key: 'costo_promedio', width: 16 },
              { header: '% valor inventario', key: 'participacion_valor_pct', width: 18 },
              { header: 'Agrupacion', key: 'ctx_group_by', width: 14 },
              { header: 'Filtro producto', key: 'ctx_producto', width: 24 },
              { header: 'Filtro bodega', key: 'ctx_bodega', width: 24 },
              { header: 'Solo con stock', key: 'ctx_only_with_stock', width: 16 },
              { header: 'Exportado en', key: 'ctx_exportado_en', width: 22 },
            ],
      rows: rows.map((row) => ({
        grupo: row.groupLabel,
        categoria: row.categoria,
        sku: row.sku,
        tipo: row.tipo,
        stock_total: row.stockTotal,
        reservado_total: row.reservadoTotal,
        disponible_total: row.disponibleTotal,
        valor_total: row.valorTotal,
        costo_promedio: Number(row.stockTotal || 0) > 0 ? row.valorTotal / row.stockTotal : 0,
        participacion_valor_pct:
          valorTotalGeneral > 0 ? Number(((row.valorTotal / valorTotalGeneral) * 100).toFixed(2)) : 0,
        ctx_group_by: filters.group_by,
        ctx_producto: filtroProductoLabel,
        ctx_bodega: filtroBodegaLabel,
        ctx_only_with_stock: onlyWithStock ? 'Si' : 'No',
        ctx_exportado_en: formatDateTimeChile(now),
      })),
    })
  }

  const handleExportPdf = async () => {
    const rows = visibleRows
    if (rows.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Reporte de inventario',
      fileName: `reporte_inventario_${getTodaySuffix()}.pdf`,
      headers:
        filters.group_by === 'bodega'
          ? ['Bodega', 'Stock', 'Valor']
          : ['Producto', 'Categoria', 'SKU', 'Tipo', 'Stock', 'Valor'],
      rows:
        filters.group_by === 'bodega'
          ? rows.map((row) => [row.groupLabel, formatNumber(row.stockTotal), formatCurrency(row.valorTotal)])
          : rows.map((row) => [
              row.groupLabel,
              row.categoria || '-',
              row.sku || '-',
              row.tipo || '-',
              formatNumber(row.stockTotal),
              formatCurrency(row.valorTotal),
            ]),
    })
  }

  const metrics = analytics?.metrics || {}
  const topValorizados = analytics?.top_valorizados || []
  const criticos = analytics?.criticos || []
  const inventoryContext = formatInventoryContext({
    groupBy: filters.group_by,
    producto: filters.producto_id ? productoById.get(String(filters.producto_id))?.nombre : '',
    bodega: filters.bodega_id ? bodegaById.get(String(filters.bodega_id))?.nombre : '',
    onlyWithStock,
  })

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Reportes de inventario</h2>
          <p className="text-sm text-muted-foreground">
            Consulta informacion detallada de inventario, agrupa resultados y exporta reportes por producto o bodega.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver resumen
          </Link>
          <Link to="/inventario/kardex" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver kardex
          </Link>
        </div>
      </div>

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4" onSubmit={onSubmit}>
        <label className="text-sm">
          Agrupar por
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.group_by}
            onChange={(event) => updateFilter('group_by', event.target.value)}
          >
            <option value="producto">Producto</option>
            <option value="bodega">Bodega</option>
          </select>
        </label>

        <label className="text-sm">
          Producto
          <SearchableSelect
            className="mt-1"
            value={filters.producto_id}
            onChange={(next) => updateFilter('producto_id', next)}
            options={productoOptions}
            ariaLabel="Producto"
            placeholder="Buscar producto..."
            emptyText="No hay productos coincidentes"
          />
        </label>

        <label className="text-sm">
          Bodega
          <SearchableSelect
            className="mt-1"
            value={filters.bodega_id}
            onChange={(next) => updateFilter('bodega_id', next)}
            options={bodegaOptions}
            ariaLabel="Bodega"
            placeholder="Buscar bodega..."
            emptyText="No hay bodegas coincidentes"
          />
        </label>

        <div className="flex items-end gap-2">
          <Button type="submit">Actualizar</Button>
          <MenuButton
            variant="outline"
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
            disabled={visibleRows.length === 0}
          />
        </div>
      </form>

      <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={onlyWithStock}
          onChange={(event) => setOnlyWithStock(event.target.checked)}
        />
        Mostrar solo items con stock mayor a 0
      </label>

      <div className="rounded-md border border-dashed border-border bg-card/60 p-4 text-sm text-muted-foreground">
        <p className="font-medium text-foreground">Contexto del analisis</p>
        <div className="mt-2 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {inventoryContext.map((line) => (
            <p key={line}>
              <span className="font-medium text-foreground">{line.split(': ')[0]}:</span> {line.split(': ')[1]}
            </p>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Registros visibles</p>
          <p className="mt-1 text-lg font-semibold">{formatNumber(metrics.registros || 0)}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Stock total</p>
          <p className="mt-1 text-lg font-semibold">{formatNumber(metrics.stock_total || 0)}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Valor inventario</p>
          <p className="mt-1 text-lg font-semibold">{formatCurrency(metrics.valor_total || 0)}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Top valorizados</p>
          <div className="mt-2 space-y-1 text-sm">
            {topValorizados.length > 0 ? (
              topValorizados.map((row, index) => (
                <p key={`${row.producto_id || row.bodega_id || index}-${index}`}>
                  {row.producto__nombre || row.bodega__nombre || '-'}:{' '}
                  <span className="font-medium">{formatCurrency(row.valor_total || 0)}</span>
                </p>
              ))
            ) : (
              <p className="text-muted-foreground">Sin datos valorizados para este filtro.</p>
            )}
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Criticos por minimo</p>
          <div className="mt-2 space-y-1 text-sm">
            {criticos.length > 0 ? (
              criticos.map((row) => (
                <p key={row.producto_id}>
                  {row.producto__nombre}: <span className="font-medium">{formatNumber(row.faltante || 0)}</span>
                </p>
              ))
            ) : (
              <p className="text-muted-foreground">Sin productos criticos para este filtro.</p>
            )}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <p className="text-sm text-muted-foreground">Detalle exportable</p>
          <h3 className="text-lg font-semibold">Inventario filtrado</h3>
        </div>
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">
                {filters.group_by === 'bodega' ? 'Bodega' : 'Producto'}
              </th>
              {filters.group_by === 'producto' ? (
                <th className="px-3 py-2 text-left font-medium">Categoria</th>
              ) : null}
              {filters.group_by === 'producto' ? (
                <th className="px-3 py-2 text-left font-medium">SKU</th>
              ) : null}
              {filters.group_by === 'producto' ? (
                <th className="px-3 py-2 text-left font-medium">Tipo</th>
              ) : null}
              <th className="px-3 py-2 text-left font-medium">Stock</th>
              <th className="px-3 py-2 text-left font-medium">Valor</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.length > 0 ? (
              visibleRows.map((row, index) => (
                <tr key={`${filters.group_by}-${index}`} className="border-t border-border">
                  <td className="px-3 py-2">{row.groupLabel}</td>
                  {filters.group_by === 'producto' ? <td className="px-3 py-2">{row.categoria || '-'}</td> : null}
                  {filters.group_by === 'producto' ? <td className="px-3 py-2">{row.sku || '-'}</td> : null}
                  {filters.group_by === 'producto' ? <td className="px-3 py-2">{row.tipo || '-'}</td> : null}
                  <td className="px-3 py-2">{formatNumber(row.stockTotal)}</td>
                  <td className="px-3 py-2">{formatCurrency(row.valorTotal)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={filters.group_by === 'producto' ? 6 : 3}>
                  Sin datos para mostrar.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default InventarioReportesPage
