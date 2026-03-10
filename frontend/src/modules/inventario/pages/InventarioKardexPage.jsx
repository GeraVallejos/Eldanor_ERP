import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'

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

function InventarioKardexPage() {
  const [status, setStatus] = useState('idle')
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null })
  const [filters, setFilters] = useState({
    producto_id: '',
    bodega_id: '',
    tipo: '',
    documento_tipo: '',
    referencia: '',
    desde: '',
    hasta: '',
    page: 1,
    page_size: 25,
  })

  const loadCatalogs = async () => {
    try {
      const [{ data: productosData }, { data: bodegasData }] = await Promise.all([
        api.get('/productos/', { suppressGlobalErrorToast: true }),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])

      setProductos(normalizeListResponse(productosData))
      setBodegas(normalizeListResponse(bodegasData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los catalogos de inventario.' }))
    }
  }

  const fetchKardex = useCallback(async (customFilters) => {
    if (!customFilters.producto_id) {
      return
    }

    setStatus('loading')
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
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
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
    const { producto_id, bodega_id, tipo, documento_tipo, referencia, desde, hasta, page, page_size } = filters

    if (!producto_id) {
      return
    }

    const timeoutId = setTimeout(() => {
      void fetchKardex({
        producto_id,
        bodega_id,
        tipo,
        documento_tipo,
        referencia,
        desde,
        hasta,
        page,
        page_size,
      })
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [
    filters,
    filters.producto_id,
    filters.bodega_id,
    filters.tipo,
    filters.documento_tipo,
    filters.referencia,
    filters.desde,
    filters.hasta,
    filters.page,
    filters.page_size,
    fetchKardex,
  ])

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }))
  }

  const selectedProducto = useMemo(
    () => productos.find((producto) => String(producto.id) === String(filters.producto_id)),
    [productos, filters.producto_id],
  )

  const applyFilters = async (event) => {
    event.preventDefault()
    await fetchKardex({ ...filters, page: 1 })
  }

  const pageLabel = `${filters.page}`

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Kardex de inventario</h2>
        <p className="text-sm text-muted-foreground">Consulta movimientos valorizados por producto y bodega.</p>
      </div>

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4" onSubmit={applyFilters}>
        <label className="text-sm">
          Producto
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.producto_id}
            onChange={(event) => updateFilter('producto_id', event.target.value)}
            required
          >
            <option value="">Selecciona producto</option>
            {productos.map((producto) => (
              <option key={producto.id} value={producto.id}>
                {producto.nombre}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          Bodega
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.bodega_id}
            onChange={(event) => updateFilter('bodega_id', event.target.value)}
          >
            <option value="">Todas</option>
            {bodegas.map((bodega) => (
              <option key={bodega.id} value={bodega.id}>
                {bodega.nombre}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          Tipo
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.tipo}
            onChange={(event) => updateFilter('tipo', event.target.value)}
          >
            <option value="">Todos</option>
            <option value="ENTRADA">Entrada</option>
            <option value="SALIDA">Salida</option>
          </select>
        </label>

        <label className="text-sm">
          Documento
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.documento_tipo}
            onChange={(event) => updateFilter('documento_tipo', event.target.value)}
          >
            <option value="">Todos</option>
            <option value="COMPRA_RECEPCION">Compra recepcion</option>
            <option value="VENTA_FACTURA">Venta factura</option>
            <option value="AJUSTE">Ajuste</option>
            <option value="TRASLADO">Traslado</option>
            <option value="PRESUPUESTO">Presupuesto</option>
          </select>
        </label>

        <label className="text-sm">
          Desde
          <input
            type="date"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.desde}
            onChange={(event) => updateFilter('desde', event.target.value)}
          />
        </label>

        <label className="text-sm">
          Hasta
          <input
            type="date"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.hasta}
            onChange={(event) => updateFilter('hasta', event.target.value)}
          />
        </label>

        <label className="text-sm md:col-span-2">
          Referencia
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={filters.referencia}
            onChange={(event) => updateFilter('referencia', event.target.value)}
            placeholder="Buscar texto de referencia"
          />
        </label>

        <div className="flex items-end">
          <Button type="submit">Consultar</Button>
        </div>
      </form>

      {selectedProducto ? (
        <p className="text-sm text-muted-foreground">Producto seleccionado: {selectedProducto.nombre}</p>
      ) : null}

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando movimientos...</p> : null}

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
                  <td className="px-3 py-2">{row.creado_en ? String(row.creado_en).slice(0, 19).replace('T', ' ') : '-'}</td>
                  <td className="px-3 py-2">{row.tipo}</td>
                  <td className="px-3 py-2">{row.cantidad}</td>
                  <td className="px-3 py-2">{row.stock_anterior}</td>
                  <td className="px-3 py-2">{row.stock_nuevo}</td>
                  <td className="px-3 py-2">{formatMoney(row.costo_unitario)}</td>
                  <td className="px-3 py-2">{formatMoney(row.valor_total)}</td>
                  <td className="px-3 py-2">{row.documento_tipo || '-'}</td>
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
            onClick={() => setFilters((prev) => ({ ...prev, page: Math.max(prev.page - 1, 1) }))}
          >
            Anterior
          </Button>
          <span className="self-center text-xs text-muted-foreground">Pagina {pageLabel}</span>
          <Button
            size="sm"
            variant="outline"
            disabled={!pagination.next}
            onClick={() => setFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
          >
            Siguiente
          </Button>
        </div>
      </div>
    </section>
  )
}

export default InventarioKardexPage
