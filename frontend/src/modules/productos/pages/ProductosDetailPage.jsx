import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
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

function formatCostoPromedio(producto) {
  if (producto?.tipo === 'SERVICIO' || !producto?.maneja_inventario) {
    return 'No aplica'
  }

  return formatMoney(producto.costo_promedio)
}

function TrazabilidadBadge({ children, tone = 'default' }) {
  const toneClassName = {
    default: 'border-border bg-muted/40 text-foreground',
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
    info: 'border-sky-200 bg-sky-50 text-sky-900',
  }

  return (
    <span className={cn('inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium', toneClassName[tone] || toneClassName.default)}>
      {children}
    </span>
  )
}

function ProductosDetailPage() {
  const { id } = useParams()
  const [status, setStatus] = useState('idle')
  const [producto, setProducto] = useState(null)
  const [trazabilidad, setTrazabilidad] = useState({
    resumen: {
      listas_configuradas: 0,
      listas_activas_vigentes: 0,
      pedidos_venta: 0,
      documentos_compra: 0,
    },
    listas_precio: [],
    uso_documentos: {
      pedidos_venta: { cantidad: 0, ultimos: [] },
      documentos_compra: { cantidad: 0, ultimos: [] },
    },
    alertas: [],
  })
  const [trazabilidadDisponible, setTrazabilidadDisponible] = useState(true)

  useEffect(() => {
    let active = true

    const loadProducto = async () => {
      setStatus('loading')
      try {
        const [productoResult, trazabilidadResult] = await Promise.allSettled([
          api.get(`/productos/${id}/`, { suppressGlobalErrorToast: true }),
          api.get(`/productos/${id}/trazabilidad/`, { suppressGlobalErrorToast: true }),
        ])

        if (!active) {
          return
        }

        if (productoResult.status !== 'fulfilled') {
          throw productoResult.reason
        }

        setProducto(productoResult.value.data)

        if (trazabilidadResult.status === 'fulfilled') {
          setTrazabilidad(trazabilidadResult.value.data)
          setTrazabilidadDisponible(true)
        } else {
          setTrazabilidadDisponible(false)
          toast.error('No se pudo cargar la trazabilidad comercial del producto.')
        }

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
            SKU {producto.sku || '-'} | {producto.tipo || '-'} | {producto.activo ? 'Activo' : 'Inactivo'}
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

          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold">Trazabilidad comercial</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Resumen de listas de precio y referencias documentales del producto.
                </p>
              </div>
              <TrazabilidadBadge tone="info">
                {trazabilidad.resumen.listas_activas_vigentes} listas vigentes
              </TrazabilidadBadge>
            </div>

            {!trazabilidadDisponible ? (
              <p className="mt-4 text-sm text-muted-foreground">
                La trazabilidad comercial no estuvo disponible en esta carga.
              </p>
            ) : (
              <>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <DetailRow label="Listas configuradas" value={trazabilidad.resumen.listas_configuradas} />
                  <DetailRow label="Listas vigentes" value={trazabilidad.resumen.listas_activas_vigentes} />
                  <DetailRow label="Pedidos de venta" value={trazabilidad.resumen.pedidos_venta} />
                  <DetailRow label="Documentos de compra" value={trazabilidad.resumen.documentos_compra} />
                </div>

                <div className="mt-4 space-y-3">
                  <h4 className="text-sm font-semibold">Listas de precio donde el producto esta configurado</h4>
                  {trazabilidad.listas_precio.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No hay listas de precio configuradas para este producto.</p>
                  ) : (
                    <div className="space-y-2">
                      {trazabilidad.listas_precio.map((item) => (
                        <div key={item.id} className="rounded-lg border border-border bg-background/70 p-3">
                          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-sm font-medium text-foreground">{item.nombre}</p>
                              <p className="mt-1 text-xs text-muted-foreground">
                                {item.cliente_nombre || 'Lista general'} | {item.moneda_codigo || '-'} | Desde {formatDateChile(item.fecha_desde)}
                                {item.fecha_hasta ? ` hasta ${formatDateChile(item.fecha_hasta)}` : ''}
                              </p>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              <TrazabilidadBadge tone={item.esta_vigente ? 'info' : 'default'}>
                                {item.esta_vigente ? 'Vigente' : 'No vigente'}
                              </TrazabilidadBadge>
                              <TrazabilidadBadge>Precio {formatMoney(item.precio)}</TrazabilidadBadge>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
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

          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Alertas de configuracion</h3>
            <div className="mt-4 space-y-3">
              {!trazabilidadDisponible ? (
                <p className="text-sm text-muted-foreground">No fue posible evaluar alertas en esta carga.</p>
              ) : trazabilidad.alertas.length === 0 ? (
                <p className="text-sm text-muted-foreground">No se detectaron alertas de configuracion para este producto.</p>
              ) : (
                trazabilidad.alertas.map((alerta) => (
                  <div key={alerta.codigo} className="rounded-lg border border-border bg-background/70 p-3">
                    <div className="flex items-center gap-2">
                      <TrazabilidadBadge tone={alerta.nivel === 'warning' ? 'warning' : 'info'}>
                        {alerta.codigo}
                      </TrazabilidadBadge>
                    </div>
                    <p className="mt-2 text-sm text-foreground">{alerta.detalle}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Uso en documentos</h3>
            <div className="mt-4 space-y-4">
              <div>
                <p className="text-sm font-medium text-foreground">
                  Pedidos de venta recientes ({trazabilidad.uso_documentos.pedidos_venta.cantidad})
                </p>
                <div className="mt-2 space-y-2">
                  {trazabilidad.uso_documentos.pedidos_venta.ultimos.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin referencias en pedidos de venta.</p>
                  ) : (
                    trazabilidad.uso_documentos.pedidos_venta.ultimos.map((row) => (
                      <div key={row.id} className="rounded-lg border border-border bg-background/70 p-3">
                        <p className="text-sm font-medium text-foreground">{row.numero || 'Pedido sin numero'}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {row.cliente_nombre || 'Sin cliente'} | {formatDateChile(row.fecha_emision)} | {row.estado || '-'}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-foreground">
                  Documentos de compra recientes ({trazabilidad.uso_documentos.documentos_compra.cantidad})
                </p>
                <div className="mt-2 space-y-2">
                  {trazabilidad.uso_documentos.documentos_compra.ultimos.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Sin referencias en documentos de compra.</p>
                  ) : (
                    trazabilidad.uso_documentos.documentos_compra.ultimos.map((row) => (
                      <div key={row.id} className="rounded-lg border border-border bg-background/70 p-3">
                        <p className="text-sm font-medium text-foreground">{row.tipo_documento || 'Documento'} {row.folio || '-'}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {row.proveedor_nombre || 'Sin proveedor'} | {formatDateChile(row.fecha_emision)} | {row.estado || '-'}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ProductosDetailPage
