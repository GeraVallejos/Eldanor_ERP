import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import ActiveSearchFilter from '@/components/ui/ActiveSearchFilter'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import { useListGuias, ventasApi } from '@/modules/ventas/store/api'
import { VENTAS_PERMISSIONS } from '@/modules/ventas/constants'
import { formatMoney } from '@/modules/ventas/utils'
import EstadoVentaBadge from '@/modules/ventas/components/EstadoVentaBadge'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function canEditGuia(row, permissions) {
  return permissions[VENTAS_PERMISSIONS.editar] && row?.estado === 'BORRADOR'
}

function canConfirmGuia(row, permissions) {
  return permissions[VENTAS_PERMISSIONS.aprobar] && row?.estado === 'BORRADOR'
}

function canAnularGuia(row, permissions) {
  return permissions[VENTAS_PERMISSIONS.anular] && row?.estado === 'CONFIRMADA'
}

function VentasGuiasListPage() {
  const [search, setSearch] = useState('')
  const [updatingId, setUpdatingId] = useState(null)
  const { data: guias, status, reload } = useListGuias()
  const permissions = usePermissions([
    VENTAS_PERMISSIONS.crear,
    VENTAS_PERMISSIONS.editar,
    VENTAS_PERMISSIONS.aprobar,
    VENTAS_PERMISSIONS.anular,
  ])
  const canCreate = permissions[VENTAS_PERMISSIONS.crear]

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return guias.filter((row) => {
      if (!q) return true
      return (
        String(row.numero || '').toLowerCase().includes(q) ||
        String(row.estado || '').toLowerCase().includes(q) ||
        String(row.cliente_nombre || '').toLowerCase().includes(q)
      )
    })
  }, [guias, search])

  const execute = async (row, action) => {
    setUpdatingId(row.id)
    try {
      await ventasApi.executeAction(ventasApi.endpoints.guias, row.id, action, {})
      toast.success('Guia actualizada.')
      await reload()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar la guia.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold">Ventas · Guias de despacho</h2>
          <p className="text-sm text-muted-foreground">Control de despacho y salida de inventario.</p>
        </div>
        {canCreate ? <Link to="/ventas/guias/nuevo" className={cn(buttonVariants({ variant: 'default', size: 'md' }))}>Nueva guia</Link> : null}
      </div>

      <div className="flex gap-2">
        <div className="relative w-full">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                setSearch('')
              }
            }}
            placeholder="Buscar guia..."
            className="w-full rounded-md border border-border bg-background px-3 py-2 pr-9 text-sm"
          />
          {search ? (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground"
              aria-label="Limpiar busqueda"
            >
              x
            </button>
          ) : null}
        </div>
        <Button variant="outline" onClick={() => reload()}>Recargar</Button>
      </div>

      {search.trim() ? (
        <ActiveSearchFilter
          query={search}
          filteredCount={filtered.length}
          totalCount={guias.length}
          noun="guias"
          onClear={() => setSearch('')}
        />
      ) : null}

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando guias...</p> : null}

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Numero</th>
              <th className="px-3 py-2 text-left">Cliente</th>
              <th className="px-3 py-2 text-left">Estado</th>
              <th className="px-3 py-2 text-left">Fecha despacho</th>
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
                <td className="px-3 py-2">{formatDateChile(row.fecha_despacho)}</td>
                <td className="px-3 py-2 text-right">{formatMoney(row.total)}</td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-2">
                    {canEditGuia(row, permissions) ? <Link to={`/ventas/guias/${row.id}/editar`} className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}>Editar</Link> : null}
                    {canConfirmGuia(row, permissions) ? (
                      <Button size="sm" disabled={updatingId === row.id} onClick={() => execute(row, 'confirmar')}>Confirmar</Button>
                    ) : null}
                    {canAnularGuia(row, permissions) ? (
                      <Button variant="destructive" size="sm" disabled={updatingId === row.id} onClick={() => execute(row, 'anular')}>Anular</Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 ? (
              <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">Sin guias.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default VentasGuiasListPage
