import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import EstadoVentaBadge from '@/modules/ventas/components/EstadoVentaBadge'
import { VENTAS_PERMISSIONS } from '@/modules/ventas/constants'
import { useListFacturas, ventasApi } from '@/modules/ventas/store/api'
import { formatMoney } from '@/modules/ventas/utils'
import { usePermissions } from '@/modules/shared/auth/usePermission'

const canEditFactura = (row, permissions) => permissions[VENTAS_PERMISSIONS.editar] && row?.estado === 'BORRADOR'
const canEmitirFactura = (row, permissions) => permissions[VENTAS_PERMISSIONS.aprobar] && row?.estado === 'BORRADOR'
const canAnularFactura = (row, permissions) => permissions[VENTAS_PERMISSIONS.anular] && row?.estado === 'EMITIDA'

function VentasFacturasListPage() {
  const [search, setSearch] = useState('')
  const [updatingId, setUpdatingId] = useState(null)
  const { data: facturas, status, reload } = useListFacturas()
  const permissions = usePermissions([
    VENTAS_PERMISSIONS.crear,
    VENTAS_PERMISSIONS.editar,
    VENTAS_PERMISSIONS.aprobar,
    VENTAS_PERMISSIONS.anular,
  ])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return facturas.filter((row) => {
      if (!q) return true
      return (
        String(row.numero || '').toLowerCase().includes(q) ||
        String(row.estado || '').toLowerCase().includes(q) ||
        String(row.cliente_nombre || '').toLowerCase().includes(q)
      )
    })
  }, [facturas, search])

  const execute = async (row, action) => {
    setUpdatingId(row.id)
    try {
      await ventasApi.executeAction(ventasApi.endpoints.facturas, row.id, action, { motivo: `Accion ${action}` })
      toast.success('Factura actualizada.')
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar la factura.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold">Ventas · Facturas</h2>
          <p className="text-sm text-muted-foreground">Emision y anulacion de facturas con integracion a cartera.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/ventas/resumen" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Ver resumen</Link>
          <Link to="/ventas/reportes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Ver reportes</Link>
          {permissions[VENTAS_PERMISSIONS.crear] ? (
            <Link to="/ventas/facturas/nuevo" className={cn(buttonVariants({ variant: 'default', size: 'md' }))}>Nueva factura</Link>
          ) : null}
        </div>
      </div>

      <div className="flex gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar factura..."
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        <Button variant="outline" onClick={() => reload()}>Recargar</Button>
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando facturas...</p> : null}

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Numero</th>
              <th className="px-3 py-2 text-left">Cliente</th>
              <th className="px-3 py-2 text-left">Estado</th>
              <th className="px-3 py-2 text-left">Fecha emision</th>
              <th className="px-3 py-2 text-right">Total</th>
              <th className="px-3 py-2 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-card">
            {filtered.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2">{row.numero || '-'}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.cliente_nombre || '-'}</td>
                <td className="px-3 py-2"><EstadoVentaBadge estado={row.estado} /></td>
                <td className="px-3 py-2">{formatDateChile(row.fecha_emision)}</td>
                <td className="px-3 py-2 text-right">{formatMoney(row.total)}</td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-2">
                    {canEditFactura(row, permissions) ? <Link to={`/ventas/facturas/${row.id}/editar`} className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}>Editar</Link> : null}
                    {canEmitirFactura(row, permissions) ? <Button size="sm" disabled={updatingId === row.id} onClick={() => execute(row, 'emitir')}>Emitir</Button> : null}
                    {canAnularFactura(row, permissions) ? <Button variant="destructive" size="sm" disabled={updatingId === row.id} onClick={() => execute(row, 'anular')}>Anular</Button> : null}
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">Sin facturas.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default VentasFacturasListPage
