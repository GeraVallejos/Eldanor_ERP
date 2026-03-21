import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'

function DetailRow({ label, value }) {
  return (
    <div className="rounded-lg border border-border bg-background/70 p-3">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  )
}

function formatMoney(value) {
  return formatCurrencyCLP(value ?? 0)
}

function formatBoolean(value) {
  return value ? 'Si' : 'No'
}

function ProductosDetailPage() {
  const { id } = useParams()
  const [status, setStatus] = useState('idle')
  const [producto, setProducto] = useState(null)

  useEffect(() => {
    let active = true

    const loadProducto = async () => {
      setStatus('loading')
      try {
        const { data } = await api.get(`/productos/${id}/`, { suppressGlobalErrorToast: true })
        if (!active) {
          return
        }
        setProducto(data)
        setStatus('succeeded')
      } catch (error) {
        if (!active) {
          return
        }
        setStatus('failed')
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el detalle del producto.' }))
      }
    }

    if (id) {
      void loadProducto()
    }

    return () => {
      active = false
    }
  }, [id])

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando detalle del producto...</p>
  }

  if (status === 'failed') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Detalle de producto</h2>
            <p className="text-sm text-muted-foreground">No fue posible recuperar el registro solicitado.</p>
          </div>
          <Link to="/productos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
        </div>
      </section>
    )
  }

  if (!producto) {
    return null
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Catalogo de productos</p>
          <h2 className="mt-1 text-3xl font-semibold">{producto.nombre || 'Producto sin nombre'}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            SKU {producto.sku || '-'} · {producto.tipo || '-'} · {producto.activo ? 'Activo' : 'Inactivo'}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/productos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver al listado
          </Link>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Resumen maestro</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Datos comerciales y tributarios que definen el producto dentro del ERP.
            </p>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <DetailRow label="Categoria" value={producto.categoria_nombre || 'Sin categoria'} />
              <DetailRow label="Impuesto" value={producto.impuesto_nombre || 'Sin impuesto'} />
              <DetailRow label="Moneda" value={producto.moneda_codigo || '-'} />
              <DetailRow label="Unidad" value={producto.unidad_medida || '-'} />
              <DetailRow label="Precio referencia" value={formatMoney(producto.precio_referencia)} />
              <DetailRow label="Precio costo" value={formatMoney(producto.precio_costo)} />
            </div>

            <div className="mt-4 rounded-lg border border-dashed border-border px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Descripcion</p>
              <p className="mt-2 text-sm text-foreground">{producto.descripcion || 'Sin descripcion registrada.'}</p>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Configuracion operativa</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Parametros que condicionan el comportamiento del producto en inventario y documentos.
            </p>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <DetailRow label="Maneja inventario" value={formatBoolean(producto.maneja_inventario)} />
              <DetailRow label="Permite decimales" value={formatBoolean(producto.permite_decimales)} />
              <DetailRow label="Usa lotes" value={formatBoolean(producto.usa_lotes)} />
              <DetailRow label="Usa series" value={formatBoolean(producto.usa_series)} />
              <DetailRow label="Usa vencimiento" value={formatBoolean(producto.usa_vencimiento)} />
              <DetailRow label="Stock minimo" value={formatSmartNumber(producto.stock_minimo ?? 0, { maximumFractionDigits: 2 })} />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Estado actual</h3>
            <div className="mt-4 space-y-3">
              <DetailRow label="Estado" value={producto.activo ? 'Activo' : 'Inactivo'} />
              <DetailRow label="Stock actual" value={formatSmartNumber(producto.stock_actual ?? 0, { maximumFractionDigits: 2 })} />
              <DetailRow label="Costo promedio" value={formatSmartNumber(producto.costo_promedio ?? 0, { maximumFractionDigits: 4 })} />
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Notas operativas</h3>
            <p className="mt-3 text-sm text-muted-foreground">
              El stock actual y el costo promedio se administran desde inventario. Esta vista los expone como referencia
              operativa del maestro, pero no los modifica.
            </p>
            <div className="mt-4">
              <Link to="/inventario/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
                Ir a inventario
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ProductosDetailPage
