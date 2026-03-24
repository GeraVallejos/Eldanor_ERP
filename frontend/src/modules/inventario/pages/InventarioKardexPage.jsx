import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

const DOCUMENTO_TIPO_OPTIONS = [
  { value: 'GUIA_RECEPCION', label: 'Guia de recepcion' },
  { value: 'FACTURA_COMPRA', label: 'Factura de compra' },
  { value: 'VENTA_FACTURA', label: 'Venta factura' },
  { value: 'AJUSTE', label: 'Ajuste' },
  { value: 'TRASLADO', label: 'Traslado' },
  { value: 'PRESUPUESTO', label: 'Presupuesto' },
]

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function formatQuantity(value) {
  return formatSmartNumber(value, { maximumFractionDigits: 2 })
}

function formatDocumentoTipo(value) {
  if (!value) {
    return '-'
  }

  const normalized = String(value).trim().toUpperCase()
  const labels = {
    GUIA_RECEPCION: 'Guia recepcion',
    FACTURA_COMPRA: 'Factura compra',
    VENTA_FACTURA: 'Factura venta',
    AJUSTE: 'Ajuste',
    TRASLADO: 'Traslado',
    PRESUPUESTO: 'Presupuesto',
    COMPRA_RECEPCION: 'Compra recepcion',
  }

  if (labels[normalized]) {
    return labels[normalized]
  }

  return normalized.toLowerCase().replace(/_/g, ' ')
}

function normalizeFiltersForQuery(filters) {
  return {
    producto_id: filters.producto_id,
    bodega_id: filters.bodega_id,
    tipo: filters.tipo,
    documento_tipo: filters.documento_tipos.join(','),
    referencia: filters.referencia,
    desde: filters.desde,
    hasta: filters.hasta,
    page: filters.page,
    page_size: filters.page_size,
  }
}

function InventarioKardexPage() {
  const exportMenuRef = useRef(null)
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null })
  const [filters, setFilters] = useState({
    producto_id: '',
    bodega_id: '',
    tipo: '',
    documento_tipos: [],
    referencia: '',
    desde: '',
    hasta: '',
    page: 1,
    page_size: 25,
  })
  const [submittedFilters, setSubmittedFilters] = useState(null)
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const [loadingProductos, setLoadingProductos] = useState(false)

  const loadCatalogs = async () => {
    try {
      const [productosData, { data: bodegasData }] = await Promise.all([
        searchProductosCatalog({ tipo: 'PRODUCTO' }),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])

      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de inventario.' }))
    }
  }

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

  const fetchKardex = useCallback(async (customFilters) => {
    if (!customFilters.producto_id) {
      return
    }

    try {
      const { data } = await api.get('/movimientos-inventario/kardex/', {
        params: customFilters,
        suppressGlobalErrorToast: true,
      })

      setMovimientos(normalizeListResponse(data))
      setPagination({
        count: Number(data?.count || 0),
        next: data?.next || null,
        previous: data?.previous || null,
      })
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo consultar el kardex.' }))
    }
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadCatalogs()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  useEffect(() => {
    if (!submittedFilters?.producto_id) {
      return
    }

    const timeoutId = setTimeout(() => {
      void fetchKardex(submittedFilters)
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [submittedFilters, fetchKardex])

  useEffect(() => {
    if (!exportMenuOpen) {
      return undefined
    }

    const handlePointerDown = (event) => {
      if (!exportMenuRef.current?.contains(event.target)) {
        setExportMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [exportMenuOpen])

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }))
  }

  const selectedProducto = useMemo(
    () => productos.find((producto) => String(producto.id) === String(filters.producto_id)),
    [productos, filters.producto_id],
  )

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

  const bodegaById = useMemo(() => {
    const map = new Map()
    bodegas.forEach((bodega) => {
      map.set(String(bodega.id), bodega)
    })
    return map
  }, [bodegas])

  const applyFilters = async (event) => {
    event.preventDefault()
    if (!filters.producto_id) {
      toast.error('Debes seleccionar un producto.')
      return
    }
    const nextFilters = { ...filters, page: 1 }
    setFilters(nextFilters)
    setSubmittedFilters(normalizeFiltersForQuery(nextFilters))
  }

  const toggleDocumentoTipo = (value) => {
    setFilters((prev) => {
      const selected = new Set(prev.documento_tipos)
      if (selected.has(value)) {
        selected.delete(value)
      } else {
        selected.add(value)
      }
      return { ...prev, documento_tipos: Array.from(selected), page: 1 }
    })
  }

  const pageLabel = `${filters.page}`

  const getTodaySuffix = () => getChileDateSuffix()
  const productExportName = (selectedProducto?.nombre || 'producto').toLowerCase().replace(/\s+/g, '_').slice(0, 40)

  const handleExportExcel = async () => {
    if (movimientos.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'Kardex',
      fileName: `kardex_${productExportName}_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: 'Producto', key: 'producto', width: 24 },
        { header: 'SKU', key: 'producto_sku', width: 18 },
        { header: 'Bodega', key: 'bodega', width: 20 },
        { header: 'Fecha', key: 'fecha', width: 20 },
        { header: 'Tipo', key: 'tipo', width: 14 },
        { header: 'Cantidad', key: 'cantidad', width: 14 },
        { header: 'Stock anterior', key: 'stock_anterior', width: 14 },
        { header: 'Stock nuevo', key: 'stock_nuevo', width: 14 },
        { header: 'Costo unitario', key: 'costo_unitario', width: 16 },
        { header: 'Valor total', key: 'valor_total', width: 16 },
        { header: 'Documento', key: 'documento_tipo', width: 20 },
        { header: 'Referencia', key: 'referencia', width: 24 },
        { header: 'Lote', key: 'lote_codigo', width: 16 },
        { header: 'Vencimiento', key: 'fecha_vencimiento', width: 14 },
        { header: 'Series', key: 'series_codigos', width: 30 },
      ],
      rows: movimientos.map((row) => ({
        producto: selectedProducto?.nombre || String(filters.producto_id || '-'),
        producto_sku: selectedProducto?.sku || '-',
        bodega: bodegaById.get(String(row.bodega))?.nombre || String(row.bodega || '-'),
        fecha: formatDateTimeChile(row.creado_en),
        tipo: row.tipo || '-',
        cantidad: row.cantidad || 0,
        stock_anterior: row.stock_anterior || 0,
        stock_nuevo: row.stock_nuevo || 0,
        costo_unitario: Number(row.costo_unitario || 0),
        valor_total: Number(row.valor_total || 0),
        documento_tipo: formatDocumentoTipo(row.documento_tipo),
        referencia: row.referencia || '-',
        lote_codigo: row.lote_codigo || '-',
        fecha_vencimiento: row.fecha_vencimiento || '-',
        series_codigos: Array.isArray(row.series_codigos) ? row.series_codigos.join(' | ') : '-',
      })),
    })
  }

  const handleExportPdf = async () => {
    if (movimientos.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: `Kardex de inventario - ${selectedProducto?.nombre || 'Producto'}`,
      fileName: `kardex_${productExportName}_${getTodaySuffix()}.pdf`,
      headers: ['Fecha', 'Tipo', 'Cant.', 'Stock ant.', 'Stock nuevo', 'Documento', 'Referencia'],
      rows: movimientos.map((row) => [
        formatDateTimeChile(row.creado_en),
        row.tipo || '-',
        formatQuantity(row.cantidad),
        formatQuantity(row.stock_anterior),
        formatQuantity(row.stock_nuevo),
        formatDocumentoTipo(row.documento_tipo),
        String(row.referencia || '-').slice(0, 42),
      ]),
    })
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Kardex de inventario</h2>
        <p className="text-sm text-muted-foreground">Consulta movimientos valorizados por producto y bodega.</p>
      </div>

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-12" onSubmit={applyFilters}>
        <label className="text-sm font-medium md:col-span-4">
          Producto
          <SearchableSelect
            className="mt-2"
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

        <label className="text-sm font-medium md:col-span-2">
          Bodega
          <SearchableSelect
            className="mt-2"
            value={filters.bodega_id}
            onChange={(next) => updateFilter('bodega_id', next)}
            options={bodegaOptions}
            ariaLabel="Bodega"
            placeholder="Buscar bodega..."
            emptyText="No hay bodegas coincidentes"
          />
        </label>

        <label className="text-sm font-medium md:col-span-2">
          Tipo
          <select
            className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.tipo}
            onChange={(event) => updateFilter('tipo', event.target.value)}
          >
            <option value="">Todos</option>
            <option value="ENTRADA">Entrada</option>
            <option value="SALIDA">Salida</option>
          </select>
        </label>

        <label className="text-sm font-medium md:col-span-2">
          Desde
          <input
            type="date"
            className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.desde}
            onChange={(event) => updateFilter('desde', event.target.value)}
          />
        </label>

        <label className="text-sm font-medium md:col-span-2">
          Hasta
          <input
            type="date"
            className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.hasta}
            onChange={(event) => updateFilter('hasta', event.target.value)}
          />
        </label>

        <div className="rounded-md border border-border bg-muted/20 p-3 md:col-span-7">
          <p className="text-sm font-medium">Documentos</p>
          <div className="mt-2 grid grid-cols-1 gap-x-4 gap-y-1 rounded-md border border-input bg-background px-3 py-2 md:grid-cols-3">
            {DOCUMENTO_TIPO_OPTIONS.map((option) => (
              <label key={option.value} className="inline-flex items-center gap-2 py-1 text-sm leading-none">
                <input
                  type="checkbox"
                  checked={filters.documento_tipos.includes(option.value)}
                  onChange={() => toggleDocumentoTipo(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="rounded-md border border-border bg-muted/20 p-3 md:col-span-5">
          <p className="text-sm font-medium">Referencia</p>
          <input
            className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.referencia}
            onChange={(event) => updateFilter('referencia', event.target.value)}
            placeholder="Ej: GUIA 123, FACTURA 456, ANULACION"
          />

          <div className="mt-3 flex flex-wrap justify-end gap-2" ref={exportMenuRef}>
            <Button type="submit" className="min-w-28">Consultar</Button>
            <div className="relative">
              <Button
                type="button"
                variant="outline"
                className="min-w-28"
                onClick={() => setExportMenuOpen((prev) => !prev)}
                disabled={movimientos.length === 0}
              >
                Exportar
              </Button>

              {exportMenuOpen ? (
                <div className="absolute right-0 z-20 mt-2 w-40 rounded-md border border-border bg-popover p-1 shadow-md">
                  <button
                    type="button"
                    className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-muted"
                    onClick={() => {
                      setExportMenuOpen(false)
                      void handleExportExcel()
                    }}
                  >
                    Exportar Excel
                  </button>
                  <button
                    type="button"
                    className="mt-1 block w-full rounded px-3 py-2 text-left text-sm hover:bg-muted"
                    onClick={() => {
                      setExportMenuOpen(false)
                      void handleExportPdf()
                    }}
                  >
                    Exportar PDF
                  </button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </form>

      {selectedProducto ? (
        <p className="text-sm text-muted-foreground">Producto seleccionado: {selectedProducto.nombre}</p>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Fecha</th>
              <th className="px-3 py-2 text-left font-medium">Tipo</th>
              <th className="px-3 py-2 text-left font-medium">Cantidad</th>
              <th className="px-3 py-2 text-left font-medium">Stock anterior</th>
              <th className="px-3 py-2 text-left font-medium">Stock nuevo</th>
              <th className="px-3 py-2 text-left font-medium">Costo unitario</th>
              <th className="px-3 py-2 text-left font-medium">Valor total</th>
              <th className="px-3 py-2 text-left font-medium">Documento</th>
              <th className="px-3 py-2 text-left font-medium">Referencia</th>
            </tr>
          </thead>
          <tbody>
            {movimientos.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={9}>
                  Sin movimientos para los filtros seleccionados.
                </td>
              </tr>
            ) : (
              movimientos.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-3 py-2">{formatDateTimeChile(row.creado_en)}</td>
                  <td className="px-3 py-2">{row.tipo}</td>
                  <td className="px-3 py-2">{formatQuantity(row.cantidad)}</td>
                  <td className="px-3 py-2">{formatQuantity(row.stock_anterior)}</td>
                  <td className="px-3 py-2">{formatQuantity(row.stock_nuevo)}</td>
                  <td className="px-3 py-2">{formatCurrencyCLP(row.costo_unitario)}</td>
                  <td className="px-3 py-2">{formatCurrencyCLP(row.valor_total)}</td>
                  <td className="px-3 py-2">{formatDocumentoTipo(row.documento_tipo)}</td>
                  <td className="px-3 py-2">{row.referencia || '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">Total registros: {pagination.count}</p>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={!pagination.previous || filters.page <= 1}
            onClick={() => {
              setFilters((prev) => {
                const next = { ...prev, page: Math.max(prev.page - 1, 1) }
                setSubmittedFilters(normalizeFiltersForQuery(next))
                return next
              })
            }}
          >
            Anterior
          </Button>
          <span className="self-center text-xs text-muted-foreground">Pagina {pageLabel}</span>
          <Button
            size="sm"
            variant="outline"
            disabled={!pagination.next}
            onClick={() => {
              setFilters((prev) => {
                const next = { ...prev, page: prev.page + 1 }
                setSubmittedFilters(normalizeFiltersForQuery(next))
                return next
              })
            }}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </section>
  )
}

export default InventarioKardexPage
