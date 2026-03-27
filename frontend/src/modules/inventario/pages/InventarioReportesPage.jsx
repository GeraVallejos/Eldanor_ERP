import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, createSearchParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import MenuButton from '@/components/ui/MenuButton'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile, formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { inventarioApi } from '@/modules/inventario/store'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { usePermissions } from '@/modules/shared/auth/usePermission'
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

function formatDateCell(value) {
  if (!value) {
    return '-'
  }
  return formatDateTimeChile(value)
}

function formatDateOnlyCell(value) {
  if (!value) {
    return '-'
  }
  return formatDateChile(value).replaceAll('-', '/')
}

async function fetchAnalyticsSnapshot(params) {
  const { data } = await api.get('/stocks/analytics/', {
    params,
    suppressGlobalErrorToast: true,
  })
  return data
}

function buildRemediationHref(path, params) {
  const search = createSearchParams(
    Object.entries(params).reduce((acc, [key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        acc[key] = String(value)
      }
      return acc
    }, {}),
  ).toString()
  return search ? `${path}?${search}` : path
}

function InventarioReportesPage() {
  const [searchParams] = useSearchParams()
  const initialFilters = useMemo(() => ({
    group_by: searchParams.get('group_by') || 'producto',
    producto_id: searchParams.get('producto_id') || '',
    bodega_id: searchParams.get('bodega_id') || '',
  }), [searchParams])
  const initialOnlyWithStock = useMemo(
    () => !['0', 'false', 'no'].includes(String(searchParams.get('only_with_stock') || 'true').toLowerCase()),
    [searchParams],
  )
  const permissions = usePermissions(['INVENTARIO.EDITAR'])
  const canEditInventario = permissions['INVENTARIO.EDITAR']
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [filters, setFilters] = useState(initialFilters)
  const [onlyWithStock, setOnlyWithStock] = useState(initialOnlyWithStock)
  const [loadingProductos, setLoadingProductos] = useState(false)
  const [reconciliationRows, setReconciliationRows] = useState([])
  const [reconciliationPagination, setReconciliationPagination] = useState({ count: 0, next: null, previous: null })
  const [reconciliationPage, setReconciliationPage] = useState(1)
  const [loteDialogOpen, setLoteDialogOpen] = useState(false)
  const [lotesLoading, setLotesLoading] = useState(false)
  const [loteActionLoading, setLoteActionLoading] = useState(false)
  const [lotes, setLotes] = useState([])
  const [loteContext, setLoteContext] = useState(null)
  const [selectedLoteId, setSelectedLoteId] = useState('')
  const [nuevoCodigoLote, setNuevoCodigoLote] = useState('')
  const [motivoLote, setMotivoLote] = useState('')

  const loadCatalogs = useCallback(async () => {
    try {
      const [productosData, { data: bodegasData }] = await Promise.all([
        searchProductosCatalog({ tipo: 'PRODUCTO' }),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de reportes.' }))
    }
  }, [])

  const searchProductos = useCallback(async (query) => {
    setLoadingProductos(true)
    try {
      const results = await searchProductosCatalog({ query, tipo: 'PRODUCTO' })
      setProductos((prev) => mergeProductosCatalog(prev, results))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron buscar productos.' }))
    } finally {
      setLoadingProductos(false)
    }
  }, [])

  const loadAnalytics = useCallback(async (nextFilters, nextOnlyWithStock) => {
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
  }, [])

  const loadReconciliation = useCallback(async (nextFilters, page = 1) => {
    try {
      const data = await inventarioApi.getPaginated(inventarioApi.endpoints.stockReconciliation, {
        ...nextFilters,
        page,
        page_size: 20,
      })
      setReconciliationRows(data.results || [])
      setReconciliationPagination({
        count: Number(data.count || 0),
        next: data.next || null,
        previous: data.previous || null,
      })
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la conciliacion de inventario.' }))
    }
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadCatalogs()
      void loadAnalytics(initialFilters, initialOnlyWithStock)
      void loadReconciliation({
        producto_id: initialFilters.producto_id,
        bodega_id: initialFilters.bodega_id,
      }, 1)
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [initialFilters, initialOnlyWithStock, loadAnalytics, loadCatalogs, loadReconciliation])

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
    await loadAnalytics(filters, onlyWithStock)
    setReconciliationPage(1)
    await loadReconciliation({
      producto_id: filters.producto_id,
      bodega_id: filters.bodega_id,
    }, 1)
  }

  const loadLotesForRow = useCallback(async (row) => {
    if (!row?.producto_id) {
      return
    }
    setLotesLoading(true)
    try {
      const data = await inventarioApi.getList(inventarioApi.endpoints.lotes, {
        producto_id: row.producto_id,
        bodega_id: filters.bodega_id || '',
      })
      setLotes(data)
      setSelectedLoteId(data[0]?.id ? String(data[0].id) : '')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los lotes del producto.' }))
    } finally {
      setLotesLoading(false)
    }
  }, [filters.bodega_id])

  const openLoteDialog = async (row) => {
    setLoteContext(row)
    setNuevoCodigoLote('')
    setMotivoLote('')
    setLoteDialogOpen(true)
    await loadLotesForRow(row)
  }

  const closeLoteDialog = () => {
    if (loteActionLoading) {
      return
    }
    setLoteDialogOpen(false)
    setLotes([])
    setLoteContext(null)
    setSelectedLoteId('')
    setNuevoCodigoLote('')
    setMotivoLote('')
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
        producto_id: productoId,
        groupLabel: row.producto__nombre || producto?.nombre || '-',
        categoria: row.producto__categoria__nombre || '-',
        sku: producto?.sku || '-',
        tipo: producto?.tipo || '-',
        lotesActivos: row.lotes_activos || '-',
        proximoVencimiento: row.proximo_vencimiento || '-',
        seriesDisponibles: Number(row.series_disponibles || 0),
        seriesMuestra: row.series_muestra || '-',
        stockTotal: Number(row.stock_total || 0),
        reservadoTotal: Number(row.reservado_total || 0),
        disponibleTotal: Number(row.disponible_total || 0),
        valorTotal: Number(row.valor_total || 0),
      }
    })
  }, [analytics, filters.group_by, productoById])

  const visibleRows = detalleRows

  const handleExportExcel = async () => {
    const data = await fetchAnalyticsSnapshot({
      ...filters,
      only_with_stock: onlyWithStock,
    })
    const rows = Array.isArray(data?.detalle) ? data.detalle : []
    if (rows.length === 0) {
      toast.error('No hay productos para exportar con los filtros seleccionados.')
      return
    }

    const valorTotalGeneral = Number(data?.totales?.valor_total || 0)

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
            ]
          : [
              { header: 'Producto', key: 'grupo', width: 30 },
              { header: 'Categoria', key: 'categoria', width: 22 },
              { header: 'SKU', key: 'sku', width: 18 },
              { header: 'Tipo', key: 'tipo', width: 16 },
              { header: 'Lotes activos', key: 'lotes_activos', width: 24 },
              { header: 'Proximo vencimiento', key: 'proximo_vencimiento', width: 20 },
              { header: 'Series disponibles', key: 'series_disponibles', width: 18 },
              { header: 'Muestra series', key: 'series_muestra', width: 24 },
              { header: 'Stock total', key: 'stock_total', width: 14 },
              { header: 'Stock reservado', key: 'reservado_total', width: 16 },
              { header: 'Stock disponible', key: 'disponible_total', width: 16 },
              { header: 'Valor total', key: 'valor_total', width: 16 },
              { header: 'Costo promedio', key: 'costo_promedio', width: 16 },
              { header: '% valor inventario', key: 'participacion_valor_pct', width: 18 },
            ],
      rows: rows.map((row) => {
        const producto = productoById.get(String(row.producto_id || ''))
        const stockTotal = Number(row.stock_total || 0)
        const reservadoTotal = Number(row.reservado_total || 0)
        const disponibleTotal = Number(row.disponible_total || 0)
        const valorTotal = Number(row.valor_total || 0)
        const grupo = filters.group_by === 'bodega'
          ? row.bodega__nombre || '-'
          : row.producto__nombre || producto?.nombre || '-'
        return {
          grupo,
          categoria: row.producto__categoria__nombre || '-',
          sku: producto?.sku || '-',
          tipo: producto?.tipo || '-',
          lotes_activos: row.lotes_activos || '-',
          proximo_vencimiento: formatDateOnlyCell(row.proximo_vencimiento),
          series_disponibles: Number(row.series_disponibles || 0),
          series_muestra: row.series_muestra || '-',
          stock_total: stockTotal,
          reservado_total: reservadoTotal,
          disponible_total: disponibleTotal,
          valor_total: valorTotal,
          costo_promedio: stockTotal > 0 ? valorTotal / stockTotal : 0,
          participacion_valor_pct:
            valorTotalGeneral > 0 ? Number(((valorTotal / valorTotalGeneral) * 100).toFixed(2)) : 0,
        }
      }),
    })
  }

  const handleExportPdf = async () => {
    const data = await fetchAnalyticsSnapshot({
      ...filters,
      only_with_stock: onlyWithStock,
    })
    const rows = Array.isArray(data?.detalle) ? data.detalle : []
    if (rows.length === 0) {
      toast.error('No hay productos para exportar con los filtros seleccionados.')
      return
    }

    await downloadSimpleTablePdf({
      title: 'Reporte de inventario',
      fileName: `reporte_inventario_${getTodaySuffix()}.pdf`,
      headers:
        filters.group_by === 'bodega'
          ? ['Bodega', 'Stock', 'Valor']
          : ['Producto', 'Categoria', 'SKU', 'Tipo', 'Lotes activos', 'Proximo vencimiento', 'Series disponibles', 'Muestra series', 'Stock', 'Valor'],
      rows:
        filters.group_by === 'bodega'
          ? rows.map((row) => [
              row.bodega__nombre || '-',
              formatNumber(row.stock_total),
              formatCurrency(row.valor_total),
            ])
          : rows.map((row) => [
              row.producto__nombre || productoById.get(String(row.producto_id || ''))?.nombre || '-',
              row.producto__categoria__nombre || '-',
              productoById.get(String(row.producto_id || ''))?.sku || '-',
              productoById.get(String(row.producto_id || ''))?.tipo || '-',
              row.lotes_activos || '-',
              formatDateOnlyCell(row.proximo_vencimiento),
              formatNumber(row.series_disponibles || 0),
              row.series_muestra || '-',
              formatNumber(row.stock_total),
              formatCurrency(row.valor_total),
            ]),
    })
  }

  const metrics = analytics?.metrics || {}
  const topValorizados = analytics?.top_valorizados || []
  const criticos = analytics?.criticos || []
  const health = analytics?.health || {}
  const reconciliationSummary = analytics?.reconciliation || {}
  const selectedLote = useMemo(
    () => lotes.find((item) => String(item.id) === String(selectedLoteId)) || null,
    [lotes, selectedLoteId],
  )

  const handleCorregirLote = async () => {
    if (!selectedLoteId || !String(nuevoCodigoLote || '').trim() || !String(motivoLote || '').trim()) {
      return
    }
    setLoteActionLoading(true)
    try {
      await inventarioApi.executeDetailAction(
        inventarioApi.endpoints.lotes,
        selectedLoteId,
        'corregir_codigo',
        {
          payload: {
            nuevo_codigo: String(nuevoCodigoLote || '').trim().toUpperCase(),
            motivo: motivoLote.trim(),
          },
        },
      )
      toast.success('Lote corregido correctamente.')
      await Promise.all([
        loadAnalytics(filters, onlyWithStock),
        loadReconciliation({ producto_id: filters.producto_id, bodega_id: filters.bodega_id }, reconciliationPage),
        loteContext ? loadLotesForRow(loteContext) : Promise.resolve(),
      ])
      closeLoteDialog()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo corregir el lote.' }))
    } finally {
      setLoteActionLoading(false)
    }
  }

  const handleAnularLote = async () => {
    if (!selectedLoteId || !String(motivoLote || '').trim()) {
      return
    }
    setLoteActionLoading(true)
    try {
      await inventarioApi.executeDetailAction(
        inventarioApi.endpoints.lotes,
        selectedLoteId,
        'anular',
        {
          payload: {
            motivo: motivoLote.trim(),
          },
        },
      )
      toast.success('Lote anulado correctamente.')
      await Promise.all([
        loadAnalytics(filters, onlyWithStock),
        loadReconciliation({ producto_id: filters.producto_id, bodega_id: filters.bodega_id }, reconciliationPage),
        loteContext ? loadLotesForRow(loteContext) : Promise.resolve(),
      ])
      closeLoteDialog()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo anular el lote.' }))
    } finally {
      setLoteActionLoading(false)
    }
  }
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
          <Link to="/inventario/auditoria" className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}>
            Ver auditoria
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
            onSearchChange={(next) => { void searchProductos(next) }}
            options={productoOptions}
            ariaLabel="Producto"
            placeholder="Buscar producto..."
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
            disabled={false}
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
                <div key={`${row.producto_id || row.bodega_id || index}-${index}`}>
                  <p>
                    {row.producto__nombre || row.bodega__nombre || '-'}:{' '}
                    <span className="font-medium">{formatCurrency(row.valor_total || 0)}</span>
                  </p>
                  {row.producto_id && (row.lotes_activos || row.proximo_vencimiento || row.series_disponibles) ? (
                    <p className="text-xs text-muted-foreground">
                      Lotes: {row.lotes_activos || '-'} | Vence: {formatDateOnlyCell(row.proximo_vencimiento)} | Series: {formatNumber(row.series_disponibles || 0)}
                    </p>
                  ) : null}
                </div>
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
                <div key={row.producto_id}>
                  <p>
                    {row.producto__nombre}: <span className="font-medium">{formatNumber(row.faltante || 0)}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Lotes: {row.lotes_activos || '-'} | Vence: {formatDateOnlyCell(row.proximo_vencimiento)} | Series: {formatNumber(row.series_disponibles || 0)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-muted-foreground">Sin productos criticos para este filtro.</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Salud operativa</p>
          <div className="mt-3 space-y-2 text-sm">
            <p>Productos criticos: <span className="font-medium">{formatNumber(health.productos_criticos || 0)}</span></p>
            <p>Reservas activas: <span className="font-medium">{formatNumber(health.reservas_activas || 0)}</span></p>
            <p>Unidades reservadas: <span className="font-medium">{formatNumber(health.unidades_reservadas || 0)}</span></p>
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Cobertura estructural</p>
          <div className="mt-3 space-y-2 text-sm">
            <p>Bodegas con stock: <span className="font-medium">{formatNumber(health.bodegas_con_stock || 0)}</span></p>
            <p>Sin snapshot: <span className="font-medium">{formatNumber(health.sin_snapshot || 0)}</span></p>
            <p>Descuadrados vs snapshot: <span className="font-medium">{formatNumber(reconciliationSummary.count || health.descuadrados_snapshot || 0)}</span></p>
          </div>
        </div>

        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Lectura enterprise</p>
          <p className="mt-3 text-sm text-muted-foreground">
            Este panel resume criticidad, reservas y conciliacion contra el ultimo snapshot por producto y bodega.
          </p>
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
              {filters.group_by === 'producto' ? (
                <th className="px-3 py-2 text-left font-medium">Lotes activos</th>
              ) : null}
              {filters.group_by === 'producto' ? (
                <th className="px-3 py-2 text-left font-medium">Proximo vencimiento</th>
              ) : null}
              {filters.group_by === 'producto' ? (
                <th className="px-3 py-2 text-left font-medium">Series</th>
              ) : null}
              <th className="px-3 py-2 text-left font-medium">Stock</th>
              <th className="px-3 py-2 text-left font-medium">Valor</th>
              {filters.group_by === 'producto' && canEditInventario ? (
                <th className="px-3 py-2 text-left font-medium">Acciones</th>
              ) : null}
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
                  {filters.group_by === 'producto' ? <td className="px-3 py-2">{row.lotesActivos || '-'}</td> : null}
                  {filters.group_by === 'producto' ? <td className="px-3 py-2">{formatDateOnlyCell(row.proximoVencimiento)}</td> : null}
                  {filters.group_by === 'producto' ? <td className="px-3 py-2">{row.seriesDisponibles > 0 ? `${formatNumber(row.seriesDisponibles)} | ${row.seriesMuestra || '-'}` : '-'}</td> : null}
                  <td className="px-3 py-2">{formatNumber(row.stockTotal)}</td>
                  <td className="px-3 py-2">{formatCurrency(row.valorTotal)}</td>
                  {filters.group_by === 'producto' && canEditInventario ? (
                    <td className="px-3 py-2">
                      {row.producto_id && row.lotesActivos && row.lotesActivos !== '-' ? (
                        <Button type="button" size="sm" variant="outline" onClick={() => void openLoteDialog(row)}>
                          Corregir lotes
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">Sin lotes activos</span>
                      )}
                    </td>
                  ) : null}
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={filters.group_by === 'producto' ? (canEditInventario ? 10 : 9) : 3}>
                  Sin datos para mostrar.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <p className="text-sm text-muted-foreground">Conciliacion de stock</p>
          <h3 className="text-lg font-semibold">Diferencias contra ultimo snapshot</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Registros detectados: {formatNumber(reconciliationPagination.count || reconciliationSummary.count || 0)}
          </p>
        </div>
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Producto</th>
              <th className="px-3 py-2 text-left font-medium">Bodega</th>
              <th className="px-3 py-2 text-left font-medium">Stock actual</th>
              <th className="px-3 py-2 text-left font-medium">Stock snapshot</th>
              <th className="px-3 py-2 text-left font-medium">Valor actual</th>
              <th className="px-3 py-2 text-left font-medium">Valor snapshot</th>
              <th className="px-3 py-2 text-left font-medium">Ultimo snapshot</th>
              <th className="px-3 py-2 text-left font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {reconciliationRows.length > 0 ? (
              reconciliationRows.map((row, index) => (
                <tr key={`${row.producto_id}-${row.bodega_id}-${index}`} className="border-t border-border">
                  <td className="px-3 py-2">{row.producto_nombre || '-'}</td>
                  <td className="px-3 py-2">{row.bodega_nombre || '-'}</td>
                  <td className="px-3 py-2">{formatNumber(row.stock_actual)}</td>
                  <td className="px-3 py-2">{formatNumber(row.stock_snapshot)}</td>
                  <td className="px-3 py-2">{formatCurrency(row.valor_actual)}</td>
                  <td className="px-3 py-2">{formatCurrency(row.valor_snapshot)}</td>
                  <td className="px-3 py-2">{formatDateCell(row.ultimo_snapshot_en)}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      <Link
                        to={buildRemediationHref('/inventario/kardex', {
                          producto_id: row.producto_id,
                          bodega_id: row.bodega_id,
                          desde: row.ultimo_snapshot_en,
                        })}
                        className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
                      >
                        Investigar en kardex
                      </Link>
                      <Link
                        to={buildRemediationHref('/inventario/ajustes', {
                          producto_id: row.producto_id,
                          bodega_id: row.bodega_id,
                          stock_objetivo: row.stock_snapshot,
                          motivo: 'CONCILIACION SNAPSHOT',
                        })}
                        className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
                      >
                        Abrir ajuste
                      </Link>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={8}>
                  Sin diferencias detectadas contra snapshots para los filtros actuales.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <div className="flex items-center justify-between border-t border-border px-4 py-3">
          <p className="text-xs text-muted-foreground">Total diferencias: {reconciliationPagination.count}</p>
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!reconciliationPagination.previous || reconciliationPage <= 1}
              onClick={() => {
                const nextPage = Math.max(reconciliationPage - 1, 1)
                setReconciliationPage(nextPage)
                void loadReconciliation({
                  producto_id: filters.producto_id,
                  bodega_id: filters.bodega_id,
                }, nextPage)
              }}
            >
              Anterior
            </Button>
            <span className="self-center text-xs text-muted-foreground">Pagina {reconciliationPage}</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!reconciliationPagination.next}
              onClick={() => {
                const nextPage = reconciliationPage + 1
                setReconciliationPage(nextPage)
                void loadReconciliation({
                  producto_id: filters.producto_id,
                  bodega_id: filters.bodega_id,
                }, nextPage)
              }}
            >
              Siguiente
            </Button>
          </div>
        </div>
      </div>

      {loteDialogOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4">
          <div className="w-full max-w-2xl rounded-xl border border-border bg-card p-4 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold">Corregir lotes</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {loteContext?.groupLabel || 'Producto'}{filters.bodega_id ? ` | ${bodegaById.get(String(filters.bodega_id))?.nombre || 'Bodega filtrada'}` : ''}
                </p>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={closeLoteDialog} disabled={loteActionLoading}>
                Cerrar
              </Button>
            </div>

            <div className="mt-4 space-y-4">
              <label className="block text-sm">
                Lote origen
                <select
                  value={selectedLoteId}
                  onChange={(event) => setSelectedLoteId(event.target.value)}
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  disabled={lotesLoading || loteActionLoading}
                >
                  {lotes.map((lote) => (
                    <option key={lote.id} value={lote.id}>
                      {lote.lote_codigo} | Stock {formatNumber(lote.stock)} | Vence {formatDateOnlyCell(lote.fecha_vencimiento)}
                    </option>
                  ))}
                </select>
              </label>

              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-md border border-border bg-muted/20 p-3 text-sm">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Stock</p>
                  <p className="mt-1 font-medium">{formatNumber(selectedLote?.stock || 0)}</p>
                </div>
                <div className="rounded-md border border-border bg-muted/20 p-3 text-sm">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Vencimiento</p>
                  <p className="mt-1 font-medium">{formatDateOnlyCell(selectedLote?.fecha_vencimiento)}</p>
                </div>
                <div className="rounded-md border border-border bg-muted/20 p-3 text-sm">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Series disponibles</p>
                  <p className="mt-1 font-medium">{formatNumber(selectedLote?.series_disponibles || 0)}</p>
                </div>
              </div>

              <label className="block text-sm">
                Nuevo codigo de lote
                <input
                  value={nuevoCodigoLote}
                  onChange={(event) => setNuevoCodigoLote(event.target.value.toUpperCase())}
                  placeholder="Ej. 001"
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  disabled={loteActionLoading}
                />
              </label>

              <label className="block text-sm">
                Motivo de la correccion
                <textarea
                  value={motivoLote}
                  onChange={(event) => setMotivoLote(event.target.value)}
                  rows={3}
                  placeholder="Describe por que se corrige o anula este lote..."
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  disabled={loteActionLoading}
                />
              </label>

              <div className="rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                La correccion actualiza la referencia operativa del lote y deja auditoria. La anulacion solo se permite si el lote ya no tiene stock ni series disponibles.
              </div>

              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleAnularLote}
                  disabled={
                    loteActionLoading ||
                    !selectedLoteId ||
                    !String(motivoLote || '').trim() ||
                    Number(selectedLote?.stock || 0) !== 0 ||
                    Number(selectedLote?.series_disponibles || 0) > 0
                  }
                >
                  {loteActionLoading ? 'Procesando...' : 'Anular lote vacio'}
                </Button>
                <Button
                  type="button"
                  onClick={handleCorregirLote}
                  disabled={
                    loteActionLoading ||
                    !selectedLoteId ||
                    !String(nuevoCodigoLote || '').trim() ||
                    !String(motivoLote || '').trim()
                  }
                >
                  {loteActionLoading ? 'Procesando...' : 'Corregir codigo'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default InventarioReportesPage
