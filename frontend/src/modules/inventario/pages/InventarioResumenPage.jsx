import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
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

function formatMoney(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }
  return Math.round(num).toLocaleString('es-CL')
}

function InventarioResumenPage() {
  const [status, setStatus] = useState('idle')
  const [stocks, setStocks] = useState([])
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [resumen, setResumen] = useState(null)
  const [filters, setFilters] = useState({
    group_by: 'producto',
    producto_id: '',
    bodega_id: '',
  })

  const loadCatalogs = async () => {
    try {
      const [{ data: stocksData }, productosData, { data: bodegasData }] = await Promise.all([
        api.get('/stocks/', { suppressGlobalErrorToast: true }),
        getProductosCatalog(),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])
      setStocks(normalizeListResponse(stocksData))
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de resumen.' }))
    }
  }

  const loadResumen = useCallback(async (nextFilters) => {
    setStatus('loading')
    try {
      const { data } = await api.get('/stocks/resumen/', {
        params: nextFilters,
        suppressGlobalErrorToast: true,
      })
      setResumen(data)
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el resumen valorizado.' }))
    }
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadCatalogs()
      void loadResumen({
        group_by: 'producto',
        producto_id: '',
        bodega_id: '',
      })
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [loadResumen])

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

  const bodegaOptions = useMemo(
    () =>
      bodegas.map((bodega) => ({
        value: String(bodega.id),
        label: bodega.nombre || `Bodega ${bodega.id}`,
      })),
    [bodegas],
  )

  const onSubmit = async (event) => {
    event.preventDefault()
    await loadResumen(filters)
  }

  const summaryStock = useMemo(() => {
    return stocks.reduce((acc, row) => acc + Number(row.stock || 0), 0)
  }, [stocks])

  const getTodaySuffix = () => new Date().toISOString().slice(0, 10)

  const handleExportExcel = async () => {
    const rows = Array.isArray(resumen?.detalle) ? resumen.detalle : []
    if (rows.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'ResumenInventario',
      fileName: `resumen_inventario_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: filters.group_by === 'bodega' ? 'Bodega' : 'Producto', key: 'grupo', width: 30 },
        { header: 'Stock', key: 'stock_total', width: 14 },
        { header: 'Valor', key: 'valor_total', width: 16 },
      ],
      rows: rows.map((row) => ({
        grupo: row.producto__nombre || row.bodega__nombre || '-',
        stock_total: Number(row.stock_total || 0),
        valor_total: Number(row.valor_total || 0),
      })),
    })
  }

  const handleExportPdf = async () => {
    const rows = Array.isArray(resumen?.detalle) ? resumen.detalle : []
    if (rows.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Resumen valorizado de inventario',
      fileName: `resumen_inventario_${getTodaySuffix()}.pdf`,
      headers: [filters.group_by === 'bodega' ? 'Bodega' : 'Producto', 'Stock', 'Valor'],
      rows: rows.map((row) => [
        row.producto__nombre || row.bodega__nombre || '-',
        formatMoney(row.stock_total),
        formatMoney(row.valor_total),
      ]),
    })
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Resumen valorizado</h2>
        <p className="text-sm text-muted-foreground">Consolidado de stock y valor para dashboard de inventario.</p>
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
          <Button
            type="button"
            variant="outline"
            onClick={handleExportExcel}
            disabled={!Array.isArray(resumen?.detalle) || resumen.detalle.length === 0}
          >
            Excel
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleExportPdf}
            disabled={!Array.isArray(resumen?.detalle) || resumen.detalle.length === 0}
          >
            PDF
          </Button>
        </div>
      </form>

      <div className="grid gap-3 md:grid-cols-3">
        <article className="rounded-md border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Stock total (vista stocks)</p>
          <p className="text-xl font-semibold">{formatMoney(summaryStock)}</p>
        </article>

        <article className="rounded-md border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Stock total (resumen)</p>
          <p className="text-xl font-semibold">{formatMoney(resumen?.totales?.stock_total)}</p>
        </article>

        <article className="rounded-md border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground">Valor total inventario</p>
          <p className="text-xl font-semibold">{formatMoney(resumen?.totales?.valor_total)}</p>
        </article>
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Actualizando resumen...</p> : null}

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">
                {filters.group_by === 'bodega' ? 'Bodega' : 'Producto'}
              </th>
              <th className="px-3 py-2 text-left font-medium">Stock</th>
              <th className="px-3 py-2 text-left font-medium">Valor</th>
            </tr>
          </thead>
          <tbody>
            {Array.isArray(resumen?.detalle) && resumen.detalle.length > 0 ? (
              resumen.detalle.map((row, index) => (
                <tr key={`${filters.group_by}-${index}`} className="border-t border-border">
                  <td className="px-3 py-2">{row.producto__nombre || row.bodega__nombre || '-'}</td>
                  <td className="px-3 py-2">{formatMoney(row.stock_total)}</td>
                  <td className="px-3 py-2">{formatMoney(row.valor_total)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={3}>
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

export default InventarioResumenPage
