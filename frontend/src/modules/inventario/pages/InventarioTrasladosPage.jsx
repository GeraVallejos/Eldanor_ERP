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
import { getProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
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

function InventarioTrasladosPage() {
  const permissions = usePermissions(['INVENTARIO.EDITAR'])
  const canEditInventario = permissions['INVENTARIO.EDITAR']
  const [stocks, setStocks] = useState([])
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [form, setForm] = useState({ producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '' })
  const [loading, setLoading] = useState(false)
  const [historyFilters, setHistoryFilters] = useState({
    producto_id: '',
    referencia: '',
    bodega_id: '',
  })

  const loadData = async () => {
    try {
      const [{ data: stocksData }, productosData, { data: bodegasData }, { data: movimientosData }] = await Promise.all([
        api.get('/stocks/', { suppressGlobalErrorToast: true }),
        getProductosCatalog(),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
        api.get('/movimientos-inventario/', { suppressGlobalErrorToast: true }),
      ])
      setStocks(normalizeListResponse(stocksData))
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
      setMovimientos(normalizeListResponse(movimientosData).filter((row) => row.documento_tipo === 'TRASLADO'))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos de traslados.' }))
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
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

  const stockOrigenSeleccionado = useMemo(() => {
    if (!form.producto_id || !form.bodega_origen_id) return null
    const row = stocks.find((item) => String(item.producto) === String(form.producto_id) && String(item.bodega) === String(form.bodega_origen_id))
    return row ? Number(row.stock || 0) : 0
  }, [stocks, form.producto_id, form.bodega_origen_id])

  const trasladoSuperaStockOrigen =
    stockOrigenSeleccionado != null && form.cantidad && Number(form.cantidad || 0) > Number(stockOrigenSeleccionado || 0)

  const updateForm = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))
  const updateHistoryFilter = (key, value) => setHistoryFilters((prev) => ({ ...prev, [key]: value }))

  const getMovimientoProductoLabel = (row) =>
    row.producto_nombre ||
    row.producto__nombre ||
    productoById.get(String(row.producto || row.producto_id || ''))?.nombre ||
    '-'

  const getMovimientoOrigenLabel = (row) =>
    row.bodega_origen_nombre ||
    row.bodega_origen__nombre ||
    bodegaById.get(String(row.bodega_origen || row.bodega_origen_id || row.bodega || ''))?.nombre ||
    '-'

  const getMovimientoDestinoLabel = (row) =>
    row.bodega_destino_nombre ||
    row.bodega_destino__nombre ||
    bodegaById.get(String(row.bodega_destino || row.bodega_destino_id || ''))?.nombre ||
    '-'

  const visibleMovimientos = useMemo(() => {
    return movimientos.filter((row) => {
      const matchesProducto = historyFilters.producto_id
        ? String(row.producto || row.producto_id || '') === String(historyFilters.producto_id)
        : true
      const referencia = String(row.referencia || '').toLowerCase()
      const matchesReferencia = historyFilters.referencia
        ? referencia.includes(historyFilters.referencia.toLowerCase())
        : true
      const movimientoBodegas = [
        String(row.bodega_origen || row.bodega_origen_id || row.bodega || ''),
        String(row.bodega_destino || row.bodega_destino_id || ''),
      ]
      const matchesBodega = historyFilters.bodega_id
        ? movimientoBodegas.includes(String(historyFilters.bodega_id))
        : true

      return matchesProducto && matchesReferencia && matchesBodega
    })
  }, [movimientos, historyFilters])

  const handleExportExcel = async () => {
    if (visibleMovimientos.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'TrasladosInventario',
      fileName: `traslados_inventario_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Fecha', key: 'fecha', width: 22 },
        { header: 'Producto', key: 'producto', width: 30 },
        { header: 'Bodega origen', key: 'origen', width: 24 },
        { header: 'Bodega destino', key: 'destino', width: 24 },
        { header: 'Referencia', key: 'referencia', width: 32 },
        { header: 'Cantidad', key: 'cantidad', width: 14 },
      ],
      rows: visibleMovimientos.map((row) => ({
        fecha: formatDateTimeChile(row.creado_en),
        producto: getMovimientoProductoLabel(row),
        origen: getMovimientoOrigenLabel(row),
        destino: getMovimientoDestinoLabel(row),
        referencia: row.referencia || '-',
        cantidad: Number(row.cantidad || 0),
      })),
    })
  }

  const handleExportPdf = async () => {
    if (visibleMovimientos.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Traslados entre bodegas',
      fileName: `traslados_inventario_${getChileDateSuffix()}.pdf`,
      headers: ['Fecha', 'Producto', 'Origen', 'Destino', 'Referencia', 'Cantidad'],
      rows: visibleMovimientos.map((row) => [
        formatDateTimeChile(row.creado_en),
        getMovimientoProductoLabel(row),
        getMovimientoOrigenLabel(row),
        getMovimientoDestinoLabel(row),
        row.referencia || '-',
        formatNumber(row.cantidad),
      ]),
    })
  }

  const handleSubmit = async () => {
    setLoading(true)
    try {
      await api.post(
        '/movimientos-inventario/trasladar/',
        {
          producto_id: form.producto_id,
          bodega_origen_id: form.bodega_origen_id,
          bodega_destino_id: form.bodega_destino_id,
          cantidad: form.cantidad,
          referencia: `Traslado interno ${form.producto_id}`.trim(),
        },
        { suppressGlobalErrorToast: true },
      )
      toast.success('Traslado entre bodegas registrado correctamente.')
      setForm({ producto_id: '', bodega_origen_id: '', bodega_destino_id: '', cantidad: '' })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo registrar el traslado entre bodegas.' }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Traslados entre bodegas</h2>
          <p className="text-sm text-muted-foreground">Registra movimientos internos entre bodegas y revisa sus ultimos eventos.</p>
        </div>
        <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
          Volver al resumen
        </Link>
      </div>

      <div className="rounded-md border border-border bg-card p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-sm">
            Producto
            <SearchableSelect className="mt-1" value={form.producto_id} onChange={(next) => updateForm('producto_id', next)} options={productoOptions} ariaLabel="Producto traslado" placeholder="Buscar producto..." emptyText="No hay productos coincidentes" />
          </label>
          <label className="text-sm">
            Bodega origen
            <SearchableSelect className="mt-1" value={form.bodega_origen_id} onChange={(next) => updateForm('bodega_origen_id', next)} options={bodegaOptions} ariaLabel="Bodega origen" placeholder="Buscar bodega..." emptyText="No hay bodegas coincidentes" />
          </label>
          <label className="text-sm">
            Bodega destino
            <SearchableSelect className="mt-1" value={form.bodega_destino_id} onChange={(next) => updateForm('bodega_destino_id', next)} options={bodegaOptions} ariaLabel="Bodega destino" placeholder="Buscar bodega..." emptyText="No hay bodegas coincidentes" />
          </label>
          <label className="text-sm">
            Cantidad
            <input type="number" min="0" step="0.01" value={form.cantidad} onChange={(event) => updateForm('cantidad', event.target.value)} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" />
          </label>
          <div className="flex items-end">
            <Button type="button" disabled={!canEditInventario || !form.producto_id || !form.bodega_origen_id || !form.bodega_destino_id || !form.cantidad || loading} onClick={handleSubmit}>
              Registrar traslado
            </Button>
          </div>
        </div>

        {stockOrigenSeleccionado != null ? (
          <div className="rounded-md border border-border bg-muted/20 px-3 py-3 text-sm">
            <p className="font-medium">Stock actual en origen: {formatNumber(stockOrigenSeleccionado)}</p>
            {trasladoSuperaStockOrigen ? (
              <p className="mt-1 text-destructive">La cantidad solicitada supera el stock visible de la bodega origen.</p>
            ) : (
              <p className="mt-1 text-muted-foreground">Verifique igualmente reservas y movimientos simultaneos antes de confirmar.</p>
            )}
          </div>
        ) : null}
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Historial de traslados</h3>
            <p className="text-sm text-muted-foreground">Consulta, filtra y exporta movimientos internos entre bodegas.</p>
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
              options={productoOptions}
              ariaLabel="Filtrar traslados por producto"
              placeholder="Todos los productos"
              emptyText="No hay productos coincidentes"
            />
          </label>
          <label className="text-sm">
            Filtrar por bodega
            <SearchableSelect
              className="mt-1"
              value={historyFilters.bodega_id}
              onChange={(next) => updateHistoryFilter('bodega_id', next)}
              options={bodegaOptions}
              ariaLabel="Filtrar traslados por bodega"
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
              placeholder="Traslado, observacion, motivo..."
            />
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Fecha</th>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">Origen</th>
                <th className="px-3 py-2 text-left font-medium">Destino</th>
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
                  <td className="px-3 py-2">{getMovimientoOrigenLabel(row)}</td>
                  <td className="px-3 py-2">{getMovimientoDestinoLabel(row)}</td>
                  <td className="px-3 py-2">{row.referencia || '-'}</td>
                  <td className="px-3 py-2">{row.tipo || '-'}</td>
                  <td className="px-3 py-2">{formatNumber(row.cantidad)}</td>
                </tr>
              )) : <tr><td className="px-3 py-3 text-muted-foreground" colSpan={7}>No hay traslados para los filtros seleccionados.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default InventarioTrasladosPage
