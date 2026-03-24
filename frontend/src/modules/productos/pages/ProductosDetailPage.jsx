import { useEffect, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { useProductoDetail } from '@/modules/productos/store/hooks'
import { usePermissions } from '@/modules/shared/auth/usePermission'

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

function formatCostoPromedio(producto) {
  if (producto?.tipo === 'SERVICIO' || !producto?.maneja_inventario) {
    return 'No aplica'
  }

  return formatMoney(producto.costo_promedio)
}

function ScoreBadge({ score }) {
  const toneClassName = score >= 100
    ? 'border-sky-200 bg-sky-50 text-sky-900'
    : score >= 80
      ? 'border-amber-200 bg-amber-50 text-amber-900'
      : 'border-border bg-muted/40 text-foreground'

  return (
    <span className={cn('inline-flex items-center rounded-full border px-3 py-1 text-sm font-medium', toneClassName)}>
      Score {score}
    </span>
  )
}

function ProductosDetailPage() {
  const { id } = useParams()
  const permissions = usePermissions(['PRODUCTOS.EDITAR'])
  const { status, producto, gobernanza } = useProductoDetail(id)
  const hasShownDetailErrorRef = useRef(false)

  useEffect(() => {
    if (status !== 'failed' || hasShownDetailErrorRef.current) {
      return
    }

    toast.error('No se pudo cargar el detalle del producto.')
    hasShownDetailErrorRef.current = true
  }, [status])

  useEffect(() => {
    hasShownDetailErrorRef.current = false
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
            SKU {producto.sku || '-'} | {producto.tipo || '-'} | {producto.activo ? 'Activo' : 'Inactivo'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/productos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver al listado
          </Link>
          {permissions['PRODUCTOS.EDITAR'] ? (
            <Link to={`/productos/${id}/editar`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
              Editar
            </Link>
          ) : null}
          <Link to={`/productos/${id}/analisis`} className={cn(buttonVariants({ variant: gobernanza.score < 100 ? 'outline' : 'ghost', size: 'md' }))}>
            Ver analisis
          </Link>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold">Salud del maestro</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Vista resumida de calidad para el usuario operativo.
            </p>
          </div>
          <ScoreBadge score={gobernanza.score} />
        </div>

        {gobernanza.score >= 100 ? (
          <p className="mt-4 text-sm text-muted-foreground">
            El maestro del producto se encuentra saludable y no requiere investigacion adicional.
          </p>
        ) : (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Se detectaron observaciones en la configuracion del producto. Revise el analisis para ver hallazgos y contexto.
          </div>
        )}
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
              <DetailRow label="Costo promedio" value={formatCostoPromedio(producto)} />
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
