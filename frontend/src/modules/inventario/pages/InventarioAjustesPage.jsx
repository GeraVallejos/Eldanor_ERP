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
import { formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function formatNumber(value) {
  return formatSmartNumber(value, { maximumFractionDigits: 2 })
}

function InventarioAjustesPage() {
  const permissions = usePermissions(['INVENTARIO.EDITAR'])
  const canEditInventario = permissions['INVENTARIO.EDITAR']
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [form, setForm] = useState({ producto_id: '', bodega_id: '', stock_objetivo: '' })
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [historyFilters, setHistoryFilters] = useState({
    producto_id: '',
    bodega_id: '',
    referencia: '',
  })
  const [loadingProductos, setLoadingProductos] = useState(false)

  const loadCatalogs = async () => {
    try {
      const [productosData, { data: bodegasData }, { data: movimientosData }] = await Promise.all([
        searchProductosCatalog({ tipo: 'PRODUCTO' }),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
        api.get('/movimientos-inventario/', { suppressGlobalErrorToast: true }),
      ])
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
      setMovimientos(normalizeListResponse(movimientosData).filter((row) => row.documento_tipo === 'AJUSTE'))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos de ajustes de inventario.' }))
    }
  }

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

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadCatalogs()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [])

  const productoOptions = productos.map((producto) => ({
    value: String(producto.id),
    label: producto.nombre || `Producto ${producto.id}`,
    keywords: `${producto.sku || ''} ${producto.tipo || ''}`,
  }))

  const bodegaOptions = bodegas.map((bodega) => ({
    value: String(bodega.id),
    label: bodega.nombre || `Bodega ${bodega.id}`,
  }))

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

  const updateForm = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))
  const updateHistoryFilter = (key, value) => setHistoryFilters((prev) => ({ ...prev, [key]: value }))

  const getMovimientoProductoLabel = (row) =>
    row.producto_nombre ||
    row.producto__nombre ||
    productoById.get(String(row.producto || row.producto_id || ''))?.nombre ||
    '-'

  const getMovimientoBodegaLabel = (row) =>
    row.bodega_nombre ||
    row.bodega__nombre ||
    bodegaById.get(String(row.bodega || row.bodega_id || ''))?.nombre ||
    '-'

  const visibleMovimientos = useMemo(() => {
    return movimientos.filter((row) => {
      const matchesProducto = historyFilters.producto_id
        ? String(row.producto || row.producto_id || '') === String(historyFilters.producto_id)
        : true
      const matchesBodega = historyFilters.bodega_id
        ? String(row.bodega || row.bodega_id || '') === String(historyFilters.bodega_id)
        : true
      const referencia = String(row.referencia || '').toLowerCase()
      const matchesReferencia = historyFilters.referencia
        ? referencia.includes(historyFilters.referencia.toLowerCase())
        : true

      return matchesProducto && matchesBodega && matchesReferencia
    })
  }, [movimientos, historyFilters])

  const handleExportExcel = async () => {
    if (visibleMovimientos.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'AjustesInventario',
      fileName: `ajustes_inventario_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Fecha', key: 'fecha', width: 22 },
        { header: 'Producto', key: 'producto', width: 30 },
        { header: 'Bodega', key: 'bodega', width: 24 },
        { header: 'Referencia', key: 'referencia', width: 32 },
        { header: 'Tipo', key: 'tipo', width: 16 },
        { header: 'Cantidad', key: 'cantidad', width: 14 },
      ],
      rows: visibleMovimientos.map((row) => ({
        fecha: formatDateTimeChile(row.creado_en),
        producto: getMovimientoProductoLabel(row),
        bodega: getMovimientoBodegaLabel(row),
        referencia: row.referencia || '-',
        tipo: row.tipo || '-',
        cantidad: Number(row.cantidad || 0),
      })),
    })
  }

  const handleExportPdf = async () => {
    if (visibleMovimientos.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Ajustes de inventario',
      fileName: `ajustes_inventario_${getChileDateSuffix()}.pdf`,
      headers: ['Fecha', 'Producto', 'Bodega', 'Referencia', 'Tipo', 'Cantidad'],
      rows: visibleMovimientos.map((row) => [
        formatDateTimeChile(row.creado_en),
        getMovimientoProductoLabel(row),
        getMovimientoBodegaLabel(row),
        row.referencia || '-',
        row.tipo || '-',
        formatNumber(row.cantidad),
      ]),
    })
  }

  const handlePreview = async () => {
    setLoading(true)
    try {
      const { data } = await api.post(
        '/movimientos-inventario/previsualizar_regularizacion/',
        { producto_id: form.producto_id, bodega_id: form.bodega_id || null, stock_objetivo: form.stock_objetivo },
        { suppressGlobalErrorToast: true },
      )
      setPreview(data)
    } catch (error) {
      setPreview(null)
      toast.error(normalizeApiError(error, { fallback: 'No se pudo previsualizar el ajuste.' }))
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!preview?.ajustable) return
    setLoading(true)
    try {
      await api.post(
        '/movimientos-inventario/regularizar/',
        {
          producto_id: form.producto_id,
          bodega_id: form.bodega_id || null,
          stock_objetivo: form.stock_objetivo,
          referencia: `Conteo fisico ${preview.producto_nombre || ''}`.trim(),
        },
        { suppressGlobalErrorToast: true },
      )
      toast.success('Ajuste de inventario aplicado correctamente.')
      setForm({ producto_id: '', bodega_id: '', stock_objetivo: '' })
      setPreview(null)
      await loadCatalogs()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo aplicar el ajuste de inventario.' }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Ajustes de inventario</h2>
          <p className="text-sm text-muted-foreground">Previsualiza diferencias de conteo fisico y aplica regularizaciones con trazabilidad.</p>
        </div>
        <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
          Volver al resumen
        </Link>
      </div>

      <div className="rounded-md border border-border bg-card p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          <label className="text-sm">
            Producto
            <SearchableSelect className="mt-1" value={form.producto_id} onChange={(next) => updateForm('producto_id', next)} onSearchChange={(next) => { void searchProductos(next) }} options={productoOptions} ariaLabel="Producto ajuste" placeholder="Buscar producto..." emptyText="No hay productos coincidentes" loading={loadingProductos} />
          </label>
          <label className="text-sm">
            Bodega
            <SearchableSelect className="mt-1" value={form.bodega_id} onChange={(next) => updateForm('bodega_id', next)} options={bodegaOptions} ariaLabel="Bodega ajuste" placeholder="Buscar bodega..." emptyText="No hay bodegas coincidentes" />
          </label>
          <label className="text-sm">
            Stock contado
            <input type="number" min="0" step="0.01" value={form.stock_objetivo} onChange={(event) => updateForm('stock_objetivo', event.target.value)} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" />
          </label>
          <div className="flex items-end gap-2">
            <Button type="button" variant="outline" disabled={!form.producto_id || !form.stock_objetivo || loading} onClick={handlePreview}>Previsualizar</Button>
            <Button type="button" disabled={!canEditInventario || !preview?.ajustable || loading} onClick={handleApply}>Aplicar ajuste</Button>
          </div>
        </div>

        {preview ? (
          <div className="grid gap-3 rounded-md border border-border bg-muted/20 p-4 md:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Stock actual</p>
              <p className="mt-1 text-lg font-semibold">{formatNumber(preview.stock_actual)}</p>
              <p className="text-sm text-muted-foreground">Reservado: {formatNumber(preview.reservado_total)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Conteo objetivo</p>
              <p className="mt-1 text-lg font-semibold">{formatNumber(preview.stock_objetivo)}</p>
              <p className="text-sm text-muted-foreground">Disponible actual: {formatNumber(preview.disponible_actual)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Impacto</p>
              <p className="mt-1 text-lg font-semibold">{preview.tipo_movimiento || 'SIN CAMBIO'} {preview.diferencia ? `(${formatNumber(preview.diferencia)})` : ''}</p>
              <p className={`text-sm ${preview.ajustable ? 'text-muted-foreground' : 'text-destructive'}`}>{preview.ajustable ? 'Ajuste permitido' : 'Ajuste bloqueado'}</p>
            </div>
            {Array.isArray(preview.warnings) && preview.warnings.length > 0 ? <div className="md:col-span-3 rounded-md border border-border bg-background px-3 py-3 text-sm text-muted-foreground">{preview.warnings.join(' ')}</div> : null}
          </div>
        ) : null}
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Historial de ajustes</h3>
            <p className="text-sm text-muted-foreground">Filtra movimientos de regularizacion y exporta el resultado visible.</p>
          </div>
          <MenuButton
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
            disabled={visibleMovimientos.length === 0}
          />
        </div>
        <div className="mb-4 grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            Filtrar por producto
            <SearchableSelect
              className="mt-1"
              value={historyFilters.producto_id}
              onChange={(next) => updateHistoryFilter('producto_id', next)}
              onSearchChange={(next) => { void searchProductos(next) }}
              options={productoOptions}
              ariaLabel="Filtrar ajustes por producto"
              placeholder="Todos los productos"
              emptyText="No hay productos coincidentes"
              loading={loadingProductos}
            />
          </label>
          <label className="text-sm">
            Filtrar por bodega
            <SearchableSelect
              className="mt-1"
              value={historyFilters.bodega_id}
              onChange={(next) => updateHistoryFilter('bodega_id', next)}
              options={bodegaOptions}
              ariaLabel="Filtrar ajustes por bodega"
              placeholder="Todas las bodegas"
              emptyText="No hay bodegas coincidentes"
            />
          </label>
          <label className="text-sm">
            Buscar referencia
            <input
              type="text"
              value={historyFilters.referencia}
              onChange={(event) => updateHistoryFilter('referencia', event.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Conteo, ajuste, observacion..."
            />
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Fecha</th>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">Bodega</th>
                <th className="px-3 py-2 text-left font-medium">Referencia</th>
                <th className="px-3 py-2 text-left font-medium">Tipo</th>
                <th className="px-3 py-2 text-left font-medium">Cantidad</th>
              </tr>
            </thead>
            <tbody>
              {visibleMovimientos.length > 0 ? visibleMovimientos.slice(0, 50).map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-3 py-2">{formatDateTimeChile(row.creado_en)}</td>
                  <td className="px-3 py-2">{getMovimientoProductoLabel(row)}</td>
                  <td className="px-3 py-2">{getMovimientoBodegaLabel(row)}</td>
                  <td className="px-3 py-2">{row.referencia || '-'}</td>
                  <td className="px-3 py-2">{row.tipo || '-'}</td>
                  <td className="px-3 py-2">{formatNumber(row.cantidad)}</td>
                </tr>
              )) : <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>No hay ajustes para los filtros seleccionados.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default InventarioAjustesPage
