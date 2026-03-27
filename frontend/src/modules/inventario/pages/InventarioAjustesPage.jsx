import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
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

function InventarioAjustesPage() {
  const [searchParams] = useSearchParams()
  const permissions = usePermissions(['INVENTARIO.EDITAR'])
  const canEditInventario = permissions['INVENTARIO.EDITAR']
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [form, setForm] = useState({
    producto_id: searchParams.get('producto_id') || '',
    bodega_id: searchParams.get('bodega_id') || '',
    stock_objetivo: searchParams.get('stock_objetivo') || '',
    motivo: searchParams.get('motivo') || '',
    referencia_operativa: '',
    observaciones: '',
  })
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [previewError, setPreviewError] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [loadingProductos, setLoadingProductos] = useState(false)

  const loadCatalogs = async () => {
    try {
      const [productosData, bodegasData] = await Promise.all([
        searchProductosCatalog({ tipo: 'PRODUCTO' }),
        inventarioApi.getList(inventarioApi.endpoints.bodegas),
      ])
      setProductos(productosData)
      setBodegas(normalizeListResponse(bodegasData))
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

  const updateForm = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))
  const handlePreview = async () => {
    setLoading(true)
    setPreviewError(null)
    try {
      const data = await inventarioApi.postOne(
        inventarioApi.endpoints.movimientosPreviewRegularizacion,
        { producto_id: form.producto_id, bodega_id: form.bodega_id || null, stock_objetivo: form.stock_objetivo },
      )
      setPreview(data)
    } catch (error) {
      setPreview(null)
      setPreviewError(extractContractError(error, 'No se pudo previsualizar el ajuste.'))
      toast.error(normalizeApiError(error, { fallback: 'No se pudo previsualizar el ajuste.' }))
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!preview?.ajustable) return
    setLoading(true)
    setSubmitError(null)
    try {
      await inventarioApi.postOne(
        inventarioApi.endpoints.movimientosRegularizar,
        {
          producto_id: form.producto_id,
          bodega_id: form.bodega_id || null,
          stock_objetivo: form.stock_objetivo,
          referencia: buildOperationalReference({
            motivo: form.motivo,
            referenciaOperativa: form.referencia_operativa,
            observaciones: form.observaciones,
            fallback: `Conteo fisico ${preview.producto_nombre || ''}`.trim(),
          }),
        },
      )
      toast.success('Ajuste de inventario aplicado correctamente.')
      setForm({
        producto_id: '',
        bodega_id: '',
        stock_objetivo: '',
        motivo: '',
        referencia_operativa: '',
        observaciones: '',
      })
      setPreview(null)
      await loadCatalogs()
    } catch (error) {
      setSubmitError(extractContractError(error, 'No se pudo aplicar el ajuste de inventario.'))
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
        <div className="flex flex-wrap gap-2">
          <Link to="/inventario/ajustes-masivos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Modo masivo
          </Link>
          <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Ver resumen
          </Link>
        </div>
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
            <Button type="button" disabled={!canEditInventario || !preview?.ajustable || !form.motivo.trim() || loading} onClick={handleApply}>Aplicar ajuste</Button>
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
              placeholder="Conteo ciclico, merma, hallazgo de recepcion..."
            />
          </label>
          <label className="text-sm">
            Referencia operativa
            <input
              type="text"
              value={form.referencia_operativa}
              onChange={(event) => updateForm('referencia_operativa', event.target.value)}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Ticket, acta, folio o documento interno"
            />
          </label>
          <label className="text-sm md:col-span-1">
            Observaciones
            <textarea
              value={form.observaciones}
              onChange={(event) => updateForm('observaciones', event.target.value)}
              className="mt-1 min-h-24 w-full rounded-md border border-input bg-background px-3 py-2"
              placeholder="Detalle breve de la diferencia encontrada"
            />
          </label>
        </div>
        {!canEditInventario ? <ApiContractError error={{ message: 'No tiene permiso para aplicar ajustes de inventario.', errorCode: 'PERMISSION_DENIED' }} title="Acceso restringido" /> : null}
        {previewError ? <ApiContractError error={previewError} title="Error al previsualizar ajuste" /> : null}
        {submitError ? <ApiContractError error={submitError} title="Error al aplicar ajuste" /> : null}

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
            <div className="md:col-span-3 rounded-md border border-border bg-background px-3 py-3 text-sm">
              <p className="font-medium">Referencia que se registrara</p>
              <p className="mt-1 text-muted-foreground">
                {buildOperationalReference({
                  motivo: form.motivo,
                  referenciaOperativa: form.referencia_operativa,
                  observaciones: form.observaciones,
                  fallback: `Conteo fisico ${preview.producto_nombre || ''}`.trim(),
                }) || '-'}
              </p>
            </div>
            {Array.isArray(preview.warnings) && preview.warnings.length > 0 ? <div className="md:col-span-3 rounded-md border border-border bg-background px-3 py-3 text-sm text-muted-foreground">{preview.warnings.join(' ')}</div> : null}
          </div>
        ) : null}
      </div>
    </section>
  )
}

export default InventarioAjustesPage
