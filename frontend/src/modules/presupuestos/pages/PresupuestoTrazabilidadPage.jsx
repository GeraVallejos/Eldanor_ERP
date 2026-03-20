import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { usePermission } from '@/modules/shared/auth/usePermission'

const ESTADO_USO_LABELS = {
  NO_UTILIZADO: 'Sin uso comercial',
  PARCIALMENTE_UTILIZADO: 'Uso parcial',
  TOTALMENTE_UTILIZADO: 'Completamente utilizado',
}

function formatQuantity(value) {
  const amount = Number(value || 0)
  return new Intl.NumberFormat('es-CL', {
    minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

function PresupuestoTrazabilidadPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [cloning, setCloning] = useState(false)
  const [data, setData] = useState(null)
  const canCreatePresupuesto = usePermission('PRESUPUESTOS.CREAR')
  const canCreateVenta = usePermission('VENTAS.CREAR')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get(`/presupuestos/${id}/trazabilidad/`, {
        suppressGlobalErrorToast: true,
      })
      setData(response.data)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la trazabilidad comercial.' }))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [loadData])

  const consumo = data?.consumo
  const presupuesto = data?.presupuesto

  const clonePresupuesto = async () => {
    setCloning(true)
    try {
      const response = await api.post(`/presupuestos/${id}/clonar/`, {}, { suppressGlobalErrorToast: true })
      toast.success('Presupuesto clonado correctamente.')
      navigate(`/presupuestos/${response.data?.id}/editar`)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo clonar el presupuesto.' }))
    } finally {
      setCloning(false)
    }
  }

  const timeline = useMemo(() => {
    const pedidos = Array.isArray(data?.pedidos)
      ? data.pedidos.map((row) => ({ ...row, tipo: 'PEDIDO', to: `/ventas/pedidos/${row.id}` }))
      : []
    const facturas = Array.isArray(data?.facturas)
      ? data.facturas.map((row) => ({ ...row, tipo: 'FACTURA', to: '/ventas/facturas' }))
      : []

    return [...pedidos, ...facturas].sort((a, b) => String(b.fecha_emision || '').localeCompare(String(a.fecha_emision || '')))
  }, [data])

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando trazabilidad comercial...</p>
  }

  if (!data) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-semibold">Trazabilidad comercial</h2>
          <Link to="/presupuestos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
        </div>
        <p className="rounded-md border border-border bg-card px-4 py-3 text-sm text-muted-foreground">
          No fue posible cargar la informacion del presupuesto.
        </p>
      </section>
    )
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Trazabilidad comercial</h2>
          <p className="text-sm text-muted-foreground">
            Seguimiento del presupuesto, su consumo por linea y los documentos generados a partir de el.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/presupuestos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
          {consumo?.puede_generar_documentos && canCreateVenta ? (
            <>
              <Link to={`/ventas/pedidos/nuevo?presupuesto=${id}`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
                Crear pedido
              </Link>
              <Link to={`/ventas/facturas/nuevo?presupuesto=${id}`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
                Crear factura
              </Link>
            </>
          ) : !consumo?.puede_generar_documentos && canCreatePresupuesto ? (
            <Button type="button" onClick={clonePresupuesto} disabled={cloning}>
              {cloning ? 'Clonando...' : 'Clonar presupuesto'}
            </Button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 xl:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Presupuesto</p>
          <p className="mt-2 text-2xl font-semibold">#{presupuesto?.numero || '-'}</p>
          <p className="mt-1 text-sm text-muted-foreground">{presupuesto?.cliente_nombre || 'Cliente sin nombre'}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Estado de uso</p>
          <p className="mt-2 text-xl font-semibold">{ESTADO_USO_LABELS[consumo?.estado_uso] || consumo?.estado_uso || '-'}</p>
          <p className="mt-1 text-sm text-muted-foreground">Estado operativo: {presupuesto?.estado || '-'}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Cantidad usada</p>
          <p className="mt-2 text-2xl font-semibold">{formatQuantity(consumo?.cantidad_usada)}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Disponible: {formatQuantity(consumo?.cantidad_disponible)}
          </p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Valor presupuesto</p>
          <p className="mt-2 text-2xl font-semibold">{formatCurrencyCLP(presupuesto?.total || 0)}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Lineas completas: {consumo?.lineas_completas || 0} / {consumo?.lineas_totales || 0}
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.9fr)]">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Consumo por linea</h3>
            <p className="text-sm text-muted-foreground">
              Controla cuanto queda disponible del presupuesto antes de generar nuevos documentos.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Descripcion</th>
                  <th className="px-3 py-2 text-left font-medium">Cantidad</th>
                  <th className="px-3 py-2 text-left font-medium">Usada</th>
                  <th className="px-3 py-2 text-left font-medium">Disponible</th>
                  <th className="px-3 py-2 text-left font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {(consumo?.items || []).map((item) => (
                  <tr key={item.id} className="border-t border-border">
                    <td className="px-3 py-2">{item.descripcion || 'Item sin descripcion'}</td>
                    <td className="px-3 py-2">{formatQuantity(item.cantidad)}</td>
                    <td className="px-3 py-2">{formatQuantity(item.cantidad_usada)}</td>
                    <td className="px-3 py-2">{formatQuantity(item.cantidad_disponible)}</td>
                    <td className="px-3 py-2">{ESTADO_USO_LABELS[item.estado_uso] || item.estado_uso}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3">
              <h3 className="text-lg font-semibold">Hilo comercial</h3>
              <p className="text-sm text-muted-foreground">
                Vista consolidada de pedidos y facturas generados desde este presupuesto.
              </p>
            </div>
            <div className="space-y-3">
              {timeline.length === 0 ? (
                <p className="text-sm text-muted-foreground">Aun no existen documentos derivados.</p>
              ) : (
                timeline.map((row) => (
                  <div key={`${row.tipo}-${row.id}`} className="rounded-lg border border-border px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium">{row.tipo} #{row.numero || '-'}</p>
                        <p className="text-xs text-muted-foreground">
                          {row.fecha_emision || '-'} - {row.estado || '-'}
                        </p>
                      </div>
                      <p className="text-sm font-medium">{formatCurrencyCLP(row.total || 0)}</p>
                    </div>
                    <div className="mt-2">
                      <Link to={row.to} className="text-sm text-primary hover:underline">
                        Ver documento
                      </Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <h3 className="text-lg font-semibold">Criterio aplicado</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Cuando un presupuesto queda totalmente utilizado, ya no puede originar nuevos documentos y la via recomendada es clonar.
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Si el consumo es parcial, todavia puedes generar pedidos o facturas por el saldo comercial restante.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

export default PresupuestoTrazabilidadPage
