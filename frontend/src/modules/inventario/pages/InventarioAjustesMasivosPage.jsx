import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import { inventarioApi } from '@/modules/inventario/store'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function buildRow() {
  return {
    id: `${Date.now()}-${Math.random()}`,
    producto_id: '',
    bodega_id: '',
    stock_objetivo: '',
  }
}

function buildReference({ motivo, referenciaOperativa, observaciones }) {
  return [motivo, referenciaOperativa, observaciones].map((value) => String(value || '').trim()).filter(Boolean).join(' | ')
}

function InventarioAjustesMasivosPage() {
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [loadingProductos, setLoadingProductos] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loadingList, setLoadingList] = useState(false)
  const [duplicatingId, setDuplicatingId] = useState(null)
  const [lastDocument, setLastDocument] = useState(null)
  const [recentDocuments, setRecentDocuments] = useState([])
  const [filters, setFilters] = useState({ q: '', estado: 'CONFIRMADO', desde: '', hasta: '' })
  const [header, setHeader] = useState({ motivo: '', referencia_operativa: '', observaciones: '' })
  const [rows, setRows] = useState([buildRow()])

  const loadRecentDocuments = useCallback(async (nextFilters) => {
    setLoadingList(true)
    try {
      const documentosData = await inventarioApi.getPaginated(inventarioApi.endpoints.ajustesMasivos, {
        page_size: 5,
        ...(nextFilters.estado ? { estado: nextFilters.estado } : {}),
        ...(nextFilters.desde ? { desde: nextFilters.desde } : {}),
        ...(nextFilters.hasta ? { hasta: nextFilters.hasta } : {}),
        ...(nextFilters.q ? { q: nextFilters.q } : {}),
      })
      setRecentDocuments(documentosData.results || [])
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los ajustes masivos.' }))
    } finally {
      setLoadingList(false)
    }
  }, [])

  useEffect(() => {
    const loadData = async () => {
      try {
        const [productosData, bodegasData] = await Promise.all([
          searchProductosCatalog({ tipo: 'PRODUCTO' }),
          inventarioApi.getList(inventarioApi.endpoints.bodegas),
        ])
        setProductos(productosData)
        setBodegas(normalizeListResponse(bodegasData))
        await loadRecentDocuments({ q: '', estado: 'CONFIRMADO', desde: '', hasta: '' })
      } catch (error) {
        toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos del ajuste masivo.' }))
      }
    }
    void loadData()
  }, [loadRecentDocuments])

  const productoOptions = productos.map((producto) => ({
    value: String(producto.id),
    label: producto.nombre || `Producto ${producto.id}`,
    keywords: `${producto.sku || ''} ${producto.tipo || ''}`,
  }))
  const bodegaOptions = bodegas.map((bodega) => ({
    value: String(bodega.id),
    label: bodega.nombre || `Bodega ${bodega.id}`,
  }))

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

  const updateRow = (id, key, value) => {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, [key]: value } : row)))
  }

  const addRow = () => setRows((prev) => [...prev, buildRow()])
  const removeRow = (id) => setRows((prev) => (prev.length === 1 ? prev : prev.filter((row) => row.id !== id)))

  const handleSubmit = async () => {
    const referencia = buildReference(header)
    const items = rows
      .filter((row) => row.producto_id && row.stock_objetivo !== '')
      .map((row) => ({
        producto_id: row.producto_id,
        bodega_id: row.bodega_id || null,
        stock_objetivo: row.stock_objetivo,
      }))

    if (!header.motivo.trim()) {
      toast.error('Debe informar el motivo operativo del ajuste masivo.')
      return
    }
    if (items.length === 0) {
      toast.error('Debe informar al menos una linea valida.')
      return
    }

    setSaving(true)
    try {
      const data = await inventarioApi.postOne(inventarioApi.endpoints.ajustesMasivos, {
        referencia,
        motivo: header.motivo,
        observaciones: header.observaciones,
        items,
      })
      setLastDocument(data)
      await loadRecentDocuments(filters)
      setHeader({ motivo: '', referencia_operativa: '', observaciones: '' })
      setRows([buildRow()])
      toast.success('Ajuste masivo confirmado correctamente.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo confirmar el ajuste masivo.' }))
    } finally {
      setSaving(false)
    }
  }

  const handleDuplicate = async (documentoId) => {
    setDuplicatingId(documentoId)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.ajustesMasivos, documentoId, 'duplicar')
      setLastDocument(data)
      await loadRecentDocuments(filters)
      toast.success('Ajuste masivo duplicado correctamente.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo duplicar el ajuste masivo.' }))
    } finally {
      setDuplicatingId(null)
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Ajuste masivo de inventario</h2>
          <p className="text-sm text-muted-foreground">Confirma un documento con multiples regularizaciones por producto y bodega.</p>
        </div>
        <Link to="/inventario/ajustes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
          Volver a ajustes simples
        </Link>
      </div>

      <div className="rounded-md border border-border bg-card p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            Motivo operativo
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={header.motivo} onChange={(event) => setHeader((prev) => ({ ...prev, motivo: event.target.value }))} />
          </label>
          <label className="text-sm">
            Referencia operativa
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={header.referencia_operativa} onChange={(event) => setHeader((prev) => ({ ...prev, referencia_operativa: event.target.value }))} />
          </label>
          <label className="text-sm">
            Observaciones
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={header.observaciones} onChange={(event) => setHeader((prev) => ({ ...prev, observaciones: event.target.value }))} />
          </label>
        </div>

        <div className="space-y-3">
          {rows.map((row, index) => (
            <div key={row.id} className="grid gap-3 rounded-md border border-border p-3 md:grid-cols-12">
              <div className="md:col-span-5">
                <label className="text-sm">
                  Producto {index + 1}
                  <SearchableSelect className="mt-1" value={row.producto_id} onChange={(next) => updateRow(row.id, 'producto_id', next)} onSearchChange={(next) => { void searchProductos(next) }} options={productoOptions} ariaLabel={`Producto ajuste masivo ${index + 1}`} placeholder="Buscar producto..." emptyText="No hay productos coincidentes" loading={loadingProductos} />
                </label>
              </div>
              <div className="md:col-span-4">
                <label className="text-sm">
                  Bodega
                  <SearchableSelect className="mt-1" value={row.bodega_id} onChange={(next) => updateRow(row.id, 'bodega_id', next)} options={bodegaOptions} ariaLabel={`Bodega ajuste masivo ${index + 1}`} placeholder="Buscar bodega..." emptyText="No hay bodegas coincidentes" />
                </label>
              </div>
              <label className="text-sm md:col-span-2">
                Stock objetivo
                <input type="number" min="0" step="0.01" value={row.stock_objetivo} onChange={(event) => updateRow(row.id, 'stock_objetivo', event.target.value)} className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" />
              </label>
              <div className="flex items-end md:col-span-1">
                <Button type="button" variant="outline" size="sm" onClick={() => removeRow(row.id)}>Quitar</Button>
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={addRow}>Agregar linea</Button>
          <Button type="button" disabled={saving} onClick={handleSubmit}>
            {saving ? 'Confirmando...' : 'Confirmar ajuste masivo'}
          </Button>
        </div>
      </div>

      {lastDocument ? (
        <div className="rounded-md border border-border bg-card p-4">
          <h3 className="text-base font-semibold">Ultimo documento confirmado</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {lastDocument.numero} | {lastDocument.items?.length || 0} lineas | referencia {lastDocument.referencia}
          </p>
        </div>
      ) : null}

      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">Ultimos ajustes masivos</h3>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <label className="text-sm">
            Buscar
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.q} onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value }))} placeholder="Numero, motivo o referencia" />
          </label>
          <label className="text-sm">
            Estado
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.estado} onChange={(event) => setFilters((prev) => ({ ...prev, estado: event.target.value }))}>
              <option value="">Todos</option>
              <option value="CONFIRMADO">Confirmado</option>
            </select>
          </label>
          <label className="text-sm">
            Desde
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.desde} onChange={(event) => setFilters((prev) => ({ ...prev, desde: event.target.value }))} />
          </label>
          <label className="text-sm">
            Hasta
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={filters.hasta} onChange={(event) => setFilters((prev) => ({ ...prev, hasta: event.target.value }))} />
          </label>
        </div>
        <div className="mt-3 flex gap-2">
          <Button type="button" variant="outline" onClick={() => { void loadRecentDocuments(filters) }} disabled={loadingList}>
            {loadingList ? 'Consultando...' : 'Aplicar filtros'}
          </Button>
        </div>
        {recentDocuments.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Todavia no hay documentos masivos recientes.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {recentDocuments.map((documento) => (
              <div key={documento.id} className="flex flex-col gap-2 rounded-md border border-border px-3 py-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-medium">{documento.numero}</p>
                  <p className="text-xs text-muted-foreground">{documento.motivo} | {documento.items?.length || 0} lineas</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="outline" size="sm" disabled={duplicatingId === documento.id} onClick={() => { void handleDuplicate(documento.id) }}>
                    {duplicatingId === documento.id ? 'Duplicando...' : 'Duplicar'}
                  </Button>
                  <Link to={`/inventario/ajustes-masivos/${documento.id}`} className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}>
                    Ver detalle
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export default InventarioAjustesMasivosPage
