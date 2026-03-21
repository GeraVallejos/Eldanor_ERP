import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import { formatMoney } from '@/modules/ventas/utils'
import { ventasApi } from '@/modules/ventas/store/api'
import { VENTAS_PERMISSIONS } from '@/modules/ventas/constants'
import EstadoVentaBadge from '@/modules/ventas/components/EstadoVentaBadge'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function canEditPedido(pedido, permissions) {
  return permissions[VENTAS_PERMISSIONS.editar] && pedido?.estado === 'BORRADOR'
}

function canConfirmPedido(pedido, permissions) {
  return permissions[VENTAS_PERMISSIONS.aprobar] && pedido?.estado === 'BORRADOR'
}

function canAnularPedido(pedido, permissions) {
  return permissions[VENTAS_PERMISSIONS.anular] && ['BORRADOR', 'CONFIRMADO', 'EN_PROCESO'].includes(String(pedido?.estado))
}

function VentasPedidosDetailPage() {
  const { id } = useParams()
  const [status, setStatus] = useState('idle')
  const [pedido, setPedido] = useState(null)
  const [items, setItems] = useState([])
  const [updating, setUpdating] = useState(false)
  const permissions = usePermissions([
    VENTAS_PERMISSIONS.editar,
    VENTAS_PERMISSIONS.aprobar,
    VENTAS_PERMISSIONS.anular,
  ])
  const load = useCallback(async () => {
    setStatus('loading')
    try {
      const [pedidoData, itemsData] = await Promise.all([
        ventasApi.getOne(ventasApi.endpoints.pedidos, id),
        ventasApi.getList(ventasApi.endpoints.pedidosItems),
      ])
      setPedido(pedidoData)
      setItems(itemsData.filter((row) => String(row.pedido_venta) === String(id)))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el pedido.' }))
    }
  }, [id])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void load()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  const totalItems = useMemo(() => items.reduce((acc, row) => acc + Number(row.total || 0), 0), [items])

  const execute = async (action) => {
    if (!pedido) return
    setUpdating(true)
    try {
      const data = await ventasApi.executeAction(ventasApi.endpoints.pedidos, pedido.id, action, {
        motivo: `Pedido ${action} desde detalle`,
      })
      setPedido((prev) => ({ ...prev, ...data }))
      toast.success('Pedido actualizado.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el pedido.' }))
    } finally {
      setUpdating(false)
    }
  }

  if (status === 'loading') return <p className="text-sm text-muted-foreground">Cargando pedido...</p>
  if (status === 'failed' || !pedido) return <p className="text-sm text-destructive">No se pudo cargar el pedido.</p>

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold">Pedido #{pedido.numero}</h2>
          <div className="mt-1"><EstadoVentaBadge estado={pedido.estado} /></div>
        </div>
        <div className="flex gap-2">
          {canEditPedido(pedido, permissions) ? <Link to={`/ventas/pedidos/${pedido.id}/editar`} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Editar</Link> : null}
          {canConfirmPedido(pedido, permissions) ? <Button disabled={updating} onClick={() => execute('confirmar')}>Confirmar</Button> : null}
          {canAnularPedido(pedido, permissions) ? (
            <Button disabled={updating} variant="destructive" onClick={() => execute('anular')}>Anular</Button>
          ) : null}
          <Link to="/ventas/pedidos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
        </div>
      </div>

      <div className="grid gap-3 rounded-md border border-border bg-card p-4 sm:grid-cols-2">
        <div>
          <p className="text-xs text-muted-foreground">Fecha emision</p>
          <p className="text-sm">{formatDateChile(pedido.fecha_emision)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Fecha entrega</p>
          <p className="text-sm">{formatDateChile(pedido.fecha_entrega)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Subtotal</p>
          <p className="text-sm">{formatMoney(pedido.subtotal)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Total</p>
          <p className="text-sm font-medium">{formatMoney(pedido.total)}</p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Descripcion</th>
              <th className="px-3 py-2 text-right">Cantidad</th>
              <th className="px-3 py-2 text-right">Precio</th>
              <th className="px-3 py-2 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-card">
            {items.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2">{row.descripcion || '-'}</td>
                <td className="px-3 py-2 text-right">{row.cantidad}</td>
                <td className="px-3 py-2 text-right">{formatMoney(row.precio_unitario)}</td>
                <td className="px-3 py-2 text-right">{formatMoney(row.total)}</td>
              </tr>
            ))}
            <tr>
              <td colSpan={3} className="px-3 py-2 text-right font-medium">Total items</td>
              <td className="px-3 py-2 text-right font-semibold">{formatMoney(totalItems)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default VentasPedidosDetailPage
