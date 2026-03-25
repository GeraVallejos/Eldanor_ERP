import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import ApiContractError from '@/components/ui/ApiContractError'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { inventarioApi } from '@/modules/inventario/store'
import { mergeProductosCatalog, searchProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function formatNumber(value) {
  return formatSmartNumber(value, { maximumFractionDigits: 2 })
}

function buildOperationalReference({ motivo, referenciaOperativa, observaciones, fallback }) {
  const parts = [motivo, referenciaOperativa, observaciones].map((value) => String(value || '').trim()).filter(Boolean)
  if (parts.length > 0) {
    return parts.join(' | ')
  }
  return String(fallback || '').trim()
}

function extractContractError(error, fallback) {
  return {
    message: fallback,
    detail: error?.response?.data?.detail ?? null,
    errorCode: error?.response?.data?.error_code ?? null,
  }
}

function InventarioTrasladosPage() {
  const permissions = usePermissions(['INVENTARIO.EDITAR'])
  const canEditInventario = permissions['INVENTARIO.EDITAR']
  const [stocks, setStocks] = useState([])
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [form, setForm] = useState({
    producto_id: '',
    bodega_origen_id: '',
    bodega_destino_id: '',
    cantidad: '',
    motivo: '',
    referencia_operativa: '',
    observaciones: '',
  })
  const [loading, setLoading] = useState(false)
  const [submitError, setSubmitError] = useState(null)
  const [loadingProductos, setLoadingProductos] = useState(false)

  const loadData = async () => {
    try {
      const [stocksData, productosData, bodegasData] = await Promise.all([
        inventarioApi.getList(inventarioApi.endpoints.stocks),
        searchProductosCatalog({ tipo: 'PRODUCTO' }),
        inventarioApi.getList(inventarioApi.endpoints.bodegas),
      ])
      setStocks(normalizeListResponse(stocksData))
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos de traslados.' }))
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

  const stockOrigenSeleccionado = useMemo(() => {
    if (!form.producto_id || !form.bodega_origen_id) return null
    const row = stocks.find((item) => String(item.producto) === String(form.producto_id) && String(item.bodega) === String(form.bodega_origen_id))
    return row ? Number(row.stock || 0) : 0
  }, [stocks, form.producto_id, form.bodega_origen_id])

  const trasladoSuperaStockOrigen =
    stockOrigenSeleccionado != null && form.cantidad && Number(form.cantidad || 0) > Number(stockOrigenSeleccionado || 0)

  const updateForm = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))
  const handleSubmit = async () => {
    setLoading(true)
    setSubmitError(null)
    try {
      await inventarioApi.postOne(
        inventarioApi.endpoints.movimientosTrasladar,
        {
          producto_id: form.producto_id,
          bodega_origen_id: form.bodega_origen_id,
          bodega_destino_id: form.bodega_destino_id,
          cantidad: form.cantidad,
          referencia: buildOperationalReference({
            motivo: form.motivo,
            referenciaOperativa: form.referencia_operativa,
            observaciones: form.observaciones,
            fallback: `Traslado interno ${form.producto_id}`.trim(),
          }),
        },
      )
      toast.success('Traslado entre bodegas registrado correctamente.')
      setForm({
        producto_id: '',
        bodega_origen_id: '',
        bodega_destino_id: '',
        cantidad: '',
        motivo: '',
        referencia_operativa: '',
        observaciones: '',
      })
      await loadData()
    } catch (error) {
      setSubmitError(extractContractError(error, 'No se pudo registrar el traslado entre bodegas.'))
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
        <div className="flex flex-wrap gap-2">
          <Link to="/inventario/traslados-masivos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Modo masivo
          </Link>
          <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Ver resumen
          </Link>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card p-4 space-y-4">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-sm">
            Producto
            <SearchableSelect className="mt-1" value={form.producto_id} onChange={(next) => updateForm('producto_id', next)} onSearchChange={(next) => { void searchProductos(next) }} options={productoOptions} ariaLabel="Producto traslado" placeholder="Buscar producto..." emptyText="No hay productos coincidentes" loading={loadingProductos} />
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
            <Button type="button" disabled={!canEditInventario || !form.producto_id || !form.bodega_origen_id || !form.bodega_destino_id || !form.cantidad || !form.motivo.trim() || loading} onClick={handleSubmit}>
              Registrar traslado
            </Button>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-sm">
            Motivo operativo
            <input
              type="text"
              value={form.motivo}
              onChange={(event) => updateForm('motivo', event.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Reposicion sucursal, consolidacion, contingencia..."
            />
          </label>
          <label className="text-sm">
            Referencia operativa
            <input
              type="text"
              value={form.referencia_operativa}
              onChange={(event) => updateForm('referencia_operativa', event.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Ticket, OT, folio logistico o solicitud interna"
            />
          </label>
          <label className="text-sm">
            Observaciones
            <textarea
              value={form.observaciones}
              onChange={(event) => updateForm('observaciones', event.target.value)}
              className="mt-1 min-h-24 w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Aclaraciones para el equipo de bodega o auditoria"
            />
          </label>
        </div>
        {!canEditInventario ? <ApiContractError error={{ message: 'No tiene permiso para registrar traslados de inventario.', errorCode: 'PERMISSION_DENIED' }} title="Acceso restringido" /> : null}
        {submitError ? <ApiContractError error={submitError} title="Error al registrar traslado" /> : null}

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
        {(form.motivo || form.referencia_operativa || form.observaciones) ? (
          <div className="rounded-md border border-border bg-muted/20 px-3 py-3 text-sm">
            <p className="font-medium">Referencia que se registrara</p>
            <p className="mt-1 text-muted-foreground">
              {buildOperationalReference({
                motivo: form.motivo,
                referenciaOperativa: form.referencia_operativa,
                observaciones: form.observaciones,
                fallback: `Traslado interno ${form.producto_id}`.trim(),
              }) || '-'}
            </p>
          </div>
        ) : null}
      </div>
    </section>
  )
}

export default InventarioTrasladosPage
