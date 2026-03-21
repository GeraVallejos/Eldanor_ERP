import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import MenuButton from '@/components/ui/MenuButton'
import { formatDateChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { cn } from '@/lib/utils'
import { useListPedidos, ventasApi } from '@/modules/ventas/store/api'
import { VENTAS_PERMISSIONS } from '@/modules/ventas/constants'
import { formatMoney } from '@/modules/ventas/utils'
import EstadoVentaBadge from '@/modules/ventas/components/EstadoVentaBadge'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function canEditPedido(row, permissions) {
  return permissions[VENTAS_PERMISSIONS.editar] && row?.estado === 'BORRADOR'
}

function canConfirmPedido(row, permissions) {
  return permissions[VENTAS_PERMISSIONS.aprobar] && row?.estado === 'BORRADOR'
}

function canAnularPedido(row, permissions) {
  return permissions[VENTAS_PERMISSIONS.anular] && ['BORRADOR', 'CONFIRMADO', 'EN_PROCESO'].includes(String(row?.estado))
}

function VentasPedidosListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [estado, setEstado] = useState('')
  const [updatingId, setUpdatingId] = useState(null)
  const { data: pedidos, status, reload, setData } = useListPedidos()

  const permissions = usePermissions([
    VENTAS_PERMISSIONS.crear,
    VENTAS_PERMISSIONS.editar,
    VENTAS_PERMISSIONS.aprobar,
    VENTAS_PERMISSIONS.anular,
  ])
  const canCreate = permissions[VENTAS_PERMISSIONS.crear]

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return pedidos.filter((row) => {
      if (estado && row.estado !== estado) return false
      if (!q) return true
      return (
        String(row.numero || '').toLowerCase().includes(q) ||
        String(row.estado || '').toLowerCase().includes(q) ||
        String(row.cliente_nombre || '').toLowerCase().includes(q)
      )
    })
  }, [pedidos, search, estado])

  const updateState = async (row, action, payload = {}) => {
    setUpdatingId(row.id)
    try {
      const updated = await ventasApi.executeAction(ventasApi.endpoints.pedidos, row.id, action, payload)
      setData((prev) => prev.map((item) => (String(item.id) === String(row.id) ? { ...item, ...updated } : item)))
      toast.success('Pedido actualizado correctamente.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el pedido.' }))
    } finally {
      setUpdatingId(null)
    }
  }

  const handleExportExcel = async () => {
    await downloadExcelFile({
      sheetName: 'PedidosVenta',
      fileName: `pedidos_venta_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Numero', key: 'numero', width: 16 },
        { header: 'Estado', key: 'estado', width: 16 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 16 },
        { header: 'Total', key: 'total', width: 16 },
      ],
      rows: filtered.map((row) => ({
        numero: row.numero || '-',
        estado: row.estado || '-',
        fecha_emision: formatDateChile(row.fecha_emision),
        total: Number(row.total || 0),
      })),
    })
  }

  const handleExportPdf = async () => {
    await downloadSimpleTablePdf({
      title: 'Pedidos de venta',
      fileName: `pedidos_venta_${getChileDateSuffix()}.pdf`,
      headers: ['Numero', 'Estado', 'Fecha emision', 'Total'],
      rows: filtered.map((row) => [
        row.numero || '-',
        row.estado || '-',
        formatDateChile(row.fecha_emision),
        formatMoney(row.total),
      ]),
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Ventas · Pedidos</h2>
          <p className="text-sm text-muted-foreground">Gestione cotizaciones confirmadas y pedidos comerciales.</p>
        </div>
        <div className="flex items-center gap-2">
          <MenuButton variant="outline" onExportExcel={handleExportExcel} onExportPdf={handleExportPdf} />
          {canCreate ? (
            <Link to="/ventas/pedidos/nuevo" className={cn(buttonVariants({ variant: 'default', size: 'md' }))}>
              Nuevo pedido
            </Link>
          ) : null}
        </div>
      </div>

      <div className="grid gap-2 rounded-md border border-border bg-card p-3 sm:grid-cols-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por numero o estado..."
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        <select
          value={estado}
          onChange={(e) => setEstado(e.target.value)}
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="BORRADOR">BORRADOR</option>
          <option value="CONFIRMADO">CONFIRMADO</option>
          <option value="EN_PROCESO">EN_PROCESO</option>
          <option value="DESPACHADO">DESPACHADO</option>
          <option value="FACTURADO">FACTURADO</option>
          <option value="ANULADO">ANULADO</option>
        </select>
        <Button variant="outline" onClick={() => reload()}>
          Recargar
        </Button>
      </div>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando pedidos...</p> : null}

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Numero</th>
              <th className="px-3 py-2 text-left font-medium">Cliente</th>
              <th className="px-3 py-2 text-left font-medium">Estado</th>
              <th className="px-3 py-2 text-left font-medium">Fecha emision</th>
              <th className="px-3 py-2 text-right font-medium">Total</th>
              <th className="px-3 py-2 text-right font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-card">
            {filtered.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2">
                  <button
                    onClick={() => navigate(`/ventas/pedidos/${row.id}`)}
                    className="font-medium text-primary hover:underline"
                  >
                    {row.numero || '-'}
                  </button>
                </td>
                <td className="px-3 py-2 text-muted-foreground">{row.cliente_nombre || '-'}</td>
                <td className="px-3 py-2"><EstadoVentaBadge estado={row.estado} /></td>
                <td className="px-3 py-2">{formatDateChile(row.fecha_emision)}</td>
                <td className="px-3 py-2 text-right">{formatMoney(row.total)}</td>
                <td className="px-3 py-2">
                  <div className="flex justify-end gap-2">
                    {canEditPedido(row, permissions) ? (
                      <Link
                        to={`/ventas/pedidos/${row.id}/editar`}
                        className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
                      >
                        Editar
                      </Link>
                    ) : null}
                    {canConfirmPedido(row, permissions) ? (
                      <Button
                        size="sm"
                        disabled={updatingId === row.id}
                        onClick={() => updateState(row, 'confirmar')}
                      >
                        Confirmar
                      </Button>
                    ) : null}
                    {canAnularPedido(row, permissions) ? (
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={updatingId === row.id}
                        onClick={() => updateState(row, 'anular', { motivo: 'Anulado desde frontend.' })}
                      >
                        Anular
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">No hay pedidos para mostrar.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default VentasPedidosListPage
