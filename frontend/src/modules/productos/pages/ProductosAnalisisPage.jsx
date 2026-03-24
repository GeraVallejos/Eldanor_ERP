import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { productosApi } from '@/modules/productos/store/api'
import { useProductoAnalisis } from '@/modules/productos/store/hooks'
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

function ProductosAnalisisPage() {
  const { id } = useParams()
  const permissions = usePermissions(['PRODUCTOS.EDITAR'])
  const {
    status,
    producto,
    trazabilidad,
    historial,
    versiones,
    gobernanza,
    reload,
    setProducto,
  } = useProductoAnalisis(id)
  const [comparacionVersiones, setComparacionVersiones] = useState(null)
  const [compareVersionDesde, setCompareVersionDesde] = useState('')
  const [compareVersionHasta, setCompareVersionHasta] = useState('')
  const [compareLoading, setCompareLoading] = useState(false)
  const [restoreTarget, setRestoreTarget] = useState(null)
  const [restoreLoading, setRestoreLoading] = useState(false)
  const hasShownLoadErrorRef = useRef(false)
  const historialPreview = historial.results.slice(0, 5)
  const versionesPreview = versiones.results.slice(0, 5)
  const versionActual = versiones.results[0]?.version ?? null

  useEffect(() => {
    if (status !== 'failed' || hasShownLoadErrorRef.current) {
      return
    }

    toast.error('No se pudo cargar el analisis del producto.')
    hasShownLoadErrorRef.current = true
  }, [status])

  useEffect(() => {
    hasShownLoadErrorRef.current = false
  }, [id])

  useEffect(() => {
    if (versiones.results.length >= 2 && !compareVersionDesde && !compareVersionHasta) {
      setCompareVersionHasta(String(versiones.results[0].version))
      setCompareVersionDesde(String(versiones.results[1].version))
    }
  }, [versiones.results, compareVersionDesde, compareVersionHasta])

  const loadVersionComparison = async (versionDesde = compareVersionDesde, versionHasta = compareVersionHasta) => {
    if (!versionDesde || !versionHasta) {
      return
    }

    setCompareLoading(true)
    try {
      const data = await productosApi.executeDetailAction(
        productosApi.endpoints.productos,
        id,
        'versiones/comparar',
        { params: { version_desde: versionDesde, version_hasta: versionHasta } },
      )
      setComparacionVersiones(data)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo comparar las versiones del producto.' }))
    } finally {
      setCompareLoading(false)
    }
  }

  const refreshAnalisis = async () => {
    await reload()
  }

  const restoreVersion = async () => {
    if (!restoreTarget || !permissions['PRODUCTOS.EDITAR']) {
      return
    }

    setRestoreLoading(true)
    try {
      const data = await productosApi.executeDetailAction(
        productosApi.endpoints.productos,
        id,
        'versiones/restaurar',
        { method: 'post', payload: { version: restoreTarget.version } },
      )
      setProducto(data.producto)
      toast.success(`Version ${data.version_restaurada} restaurada sobre el maestro.`)
      setRestoreTarget(null)
      await Promise.all([loadVersionComparison(), refreshAnalisis()])
    } catch {
      toast.error('No se pudo restaurar la version seleccionada.')
    } finally {
      setRestoreLoading(false)
    }
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando analisis del producto...</p>
  }

  if (status === 'failed') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Analisis de producto</h2>
            <p className="text-sm text-muted-foreground">No fue posible recuperar el analisis solicitado.</p>
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
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Analisis del maestro</p>
          <h2 className="mt-1 text-3xl font-semibold">{producto.nombre || 'Producto sin nombre'}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            SKU {producto.sku || '-'} | {producto.tipo || '-'} | Score {gobernanza.score}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to={`/productos/${id}`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver al detalle
          </Link>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold">Gobernanza del maestro</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Evaluacion de calidad de datos y readiness operativo del producto.
                </p>
              </div>
              <TrazabilidadBadge tone={gobernanza.estado === 'LISTO' ? 'info' : gobernanza.estado === 'OBSERVADO' ? 'warning' : 'default'}>
                Score {gobernanza.score}
              </TrazabilidadBadge>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <DetailRow label="Estado de gobierno" value={gobernanza.estado} />
              <DetailRow label="Listas vigentes" value={gobernanza.metricas?.listas_vigentes ?? 0} />
              <DetailRow label="Readiness ventas" value={formatBoolean(gobernanza.readiness?.ventas)} />
              <DetailRow label="Readiness compliance" value={formatBoolean(gobernanza.readiness?.compliance)} />
            </div>

            <div className="mt-4 space-y-3">
              {gobernanza.hallazgos.length === 0 ? (
                <p className="text-sm text-muted-foreground">No se detectaron hallazgos de gobierno para este producto.</p>
              ) : (
                gobernanza.hallazgos.map((hallazgo) => (
                  <div key={hallazgo.codigo} className="rounded-lg border border-border bg-background/70 p-3">
                    <div className="flex flex-wrap gap-2">
                      <TrazabilidadBadge tone={hallazgo.nivel === 'warning' ? 'warning' : hallazgo.nivel === 'critical' ? 'default' : 'info'}>
                        {hallazgo.codigo}
                      </TrazabilidadBadge>
                      <TrazabilidadBadge>{hallazgo.dimension}</TrazabilidadBadge>
                    </div>
                    <p className="mt-2 text-sm text-foreground">{hallazgo.detalle}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Historial del maestro</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Cambios funcionales auditados sobre el producto para seguimiento operativo.
            </p>
            <div className="mt-4 space-y-3">
              {historial.results.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay eventos auditados para este producto.</p>
              ) : (
                <>
                  {historialPreview.map((evento) => (
                    <div key={evento.id} className="rounded-lg border border-border bg-background/70 p-3">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p className="text-sm font-medium text-foreground">{evento.summary}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {evento.creado_por_email || 'Usuario no identificado'} | {formatDateChile(evento.occurred_at)}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <TrazabilidadBadge tone="default">{evento.action_code}</TrazabilidadBadge>
                          <TrazabilidadBadge tone="info">{evento.event_type}</TrazabilidadBadge>
                        </div>
                      </div>
                      {Object.keys(evento.changes || {}).length > 0 ? (
                        <div className="mt-3 rounded-lg border border-dashed border-border px-3 py-2">
                          <p className="text-xs uppercase tracking-wide text-muted-foreground">Campos afectados</p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {Object.keys(evento.changes).map((campo) => (
                              <TrazabilidadBadge key={campo}>{campo}</TrazabilidadBadge>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ))}
                  {historial.count > historialPreview.length ? (
                    <p className="text-sm text-muted-foreground">
                      Mostrando los ultimos {historialPreview.length} cambios de {historial.count} registrados.
                    </p>
                  ) : null}
                </>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="text-lg font-semibold">Versiones del maestro</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Snapshots funcionales del producto para revisar su evolucion de configuracion.
            </p>

            <div className="mt-4 space-y-3">
              {versiones.results.length >= 2 ? (
                <div className="rounded-lg border border-dashed border-border p-3">
                  <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                    <label className="text-sm">
                      Version desde
                      <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={compareVersionDesde} onChange={(event) => setCompareVersionDesde(event.target.value)}>
                        <option value="">Seleccione</option>
                        {versiones.results.map((version) => <option key={`desde-${version.id}`} value={version.version}>Version {version.version}</option>)}
                      </select>
                    </label>
                    <label className="text-sm">
                      Version hasta
                      <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={compareVersionHasta} onChange={(event) => setCompareVersionHasta(event.target.value)}>
                        <option value="">Seleccione</option>
                        {versiones.results.map((version) => <option key={`hasta-${version.id}`} value={version.version}>Version {version.version}</option>)}
                      </select>
                    </label>
                    <div className="flex items-end">
                      <Button type="button" variant="outline" onClick={() => void loadVersionComparison()} disabled={compareLoading || !compareVersionDesde || !compareVersionHasta}>
                        {compareLoading ? 'Comparando...' : 'Comparar'}
                      </Button>
                    </div>
                  </div>

                  {comparacionVersiones ? (
                    <div className="mt-3 space-y-2">
                      <p className="text-sm font-medium text-foreground">Comparacion entre versiones</p>
                      {Object.keys(comparacionVersiones.changes || {}).length === 0 ? (
                        <p className="text-sm text-muted-foreground">No se detectaron diferencias funcionales entre las versiones seleccionadas.</p>
                      ) : (
                        Object.entries(comparacionVersiones.changes).map(([field, values]) => (
                          <div key={field} className="rounded-md border border-border bg-background/70 px-3 py-2 text-sm">
                            <p className="font-medium text-foreground">{field}</p>
                            <p className="mt-1 text-muted-foreground">{String(values[0] ?? '-')} {' -> '} {String(values[1] ?? '-')}</p>
                          </div>
                        ))
                      )}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {versionesPreview.map((version) => (
                <div key={version.id} className="rounded-lg border border-border bg-background/70 p-3">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-sm font-medium text-foreground">Version {version.version}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {version.creado_por_email || 'Usuario no identificado'} | {formatDateChile(version.creado_en)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <TrazabilidadBadge tone="info">{version.event_type}</TrazabilidadBadge>
                      <TrazabilidadBadge>{Object.keys(version.changes || {}).length} cambios</TrazabilidadBadge>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <DetailRow label="Precio referencia" value={formatMoney(version.snapshot?.precio_referencia ?? 0)} />
                    <DetailRow label="Estado" value={version.snapshot?.activo === 'True' ? 'Activo' : 'Inactivo'} />
                  </div>
                  {permissions['PRODUCTOS.EDITAR'] ? (
                    <div className="mt-3">
                      <Button
                        type="button"
                        variant="outline"
                        disabled={version.version === versionActual}
                        onClick={() => setRestoreTarget({ version: version.version })}
                      >
                        {version.version === versionActual ? 'Version actual' : 'Restaurar esta version'}
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
              {versiones.count > versionesPreview.length ? (
                <p className="text-sm text-muted-foreground">
                  Mostrando las ultimas {versionesPreview.length} versiones de {versiones.count} registradas.
                </p>
              ) : null}
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

      <ConfirmDialog
        open={Boolean(restoreTarget)}
        title="Restaurar version del maestro"
        description={restoreTarget ? `Se restaurara la version ${restoreTarget.version} del producto. Esta accion generara una nueva auditoria y una nueva version.` : ''}
        confirmLabel="Restaurar"
        loading={restoreLoading}
        onCancel={() => setRestoreTarget(null)}
        onConfirm={restoreVersion}
      />
    </section>
  )
}

export default ProductosAnalisisPage
