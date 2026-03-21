import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { formatCurrencyCLP, toIntegerString } from '@/lib/numberFormat'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }
  if (Array.isArray(data?.results)) {
    return data.results
  }
  return []
}

function canApplyPayment(row, type, permissions) {
  const hasPermission = type === 'cxc' ? permissions['TESORERIA.COBRAR'] : permissions['TESORERIA.PAGAR']
  const saldo = Number(row?.saldo || 0)
  const estado = String(row?.estado || '').toUpperCase()
  return hasPermission && saldo > 0 && estado !== 'PAGADA' && estado !== 'ANULADA'
}

function TesoreriaCuentasPage() {
  const permissions = usePermissions(['TESORERIA.VER', 'TESORERIA.COBRAR', 'TESORERIA.PAGAR'])
  const [cxc, setCxc] = useState([])
  const [cxp, setCxp] = useState([])
  const [agingCxc, setAgingCxc] = useState(null)
  const [agingCxp, setAgingCxp] = useState(null)
  const [paymentState, setPaymentState] = useState({ id: '', type: '', monto: '', fecha_pago: '' })

  const loadData = async () => {
    try {
      const [{ data: cxcData }, { data: cxpData }, { data: agingCxcData }, { data: agingCxpData }] = await Promise.all([
        api.get('/cuentas-por-cobrar/', { suppressGlobalErrorToast: true }),
        api.get('/cuentas-por-pagar/', { suppressGlobalErrorToast: true }),
        api.get('/cuentas-por-cobrar/aging/', { suppressGlobalErrorToast: true }),
        api.get('/cuentas-por-pagar/aging/', { suppressGlobalErrorToast: true }),
      ])
      setCxc(normalizeListResponse(cxcData))
      setCxp(normalizeListResponse(cxpData))
      setAgingCxc(agingCxcData)
      setAgingCxp(agingCxpData)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las cuentas de tesorería.' }))
    }
  }

  useEffect(() => {
    if (permissions['TESORERIA.VER']) {
      const id = setTimeout(() => { void loadData() }, 0)
      return () => clearTimeout(id)
    }
  }, [permissions])

  const applyPayment = async (event) => {
    event.preventDefault()
    const { id, type, monto, fecha_pago } = paymentState
    if (!id || !type) {
      return
    }
    try {
      const base = type === 'cxc' ? '/cuentas-por-cobrar/' : '/cuentas-por-pagar/'
      await api.post(`${base}${id}/aplicar_pago/`, { monto, fecha_pago }, { suppressGlobalErrorToast: true })
      toast.success('Pago aplicado correctamente.')
      setPaymentState({ id: '', type: '', monto: '', fecha_pago: '' })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo aplicar el pago.' }))
    }
  }

  const renderTable = (rows, type) => (
    <div className="overflow-x-auto rounded-md border border-border bg-card">
      <table className="min-w-full text-sm">
        <thead className="bg-muted/40">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Referencia</th>
            <th className="px-3 py-2 text-left font-medium">Vencimiento</th>
            <th className="px-3 py-2 text-left font-medium">Monto</th>
            <th className="px-3 py-2 text-left font-medium">Saldo</th>
            <th className="px-3 py-2 text-left font-medium">Estado</th>
            <th className="px-3 py-2 text-left font-medium">Acción</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>Sin registros.</td></tr>
          ) : (
            rows.map((row) => (
              <tr key={row.id} className="border-t border-border">
                <td className="px-3 py-2">{row.referencia}</td>
                <td className="px-3 py-2">{row.fecha_vencimiento}</td>
                <td className="px-3 py-2">{formatCurrencyCLP(row.monto_total)}</td>
                <td className="px-3 py-2">{formatCurrencyCLP(row.saldo)}</td>
                <td className="px-3 py-2">{row.estado}</td>
                <td className="px-3 py-2">
                  {canApplyPayment(row, type, permissions) ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setPaymentState({ id: row.id, type, monto: toIntegerString(row.saldo), fecha_pago: '' })}
                    >
                      Aplicar pago
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {(type === 'cxc' ? permissions['TESORERIA.COBRAR'] : permissions['TESORERIA.PAGAR']) ? 'No aplica' : 'Sin permiso'}
                    </span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )

  const renderAgingCard = (title, aging) => {
    const totales = aging?.totales || {}
    const rows = [
      ['Al dia', totales.al_dia],
      ['1 a 30', totales['1_30']],
      ['31 a 60', totales['31_60']],
      ['61 a 90', totales['61_90']],
      ['91+', totales['91_plus']],
    ]

    return (
      <article className="rounded-md border border-border bg-card p-4">
        <p className="text-sm text-muted-foreground">{title}</p>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {rows.map(([label, value]) => (
            <div key={label} className="rounded-md border border-border/60 bg-background px-3 py-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-1 font-medium">{formatCurrencyCLP(value || 0)}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-sm font-semibold">Total: {formatCurrencyCLP(totales.total || 0)}</p>
      </article>
    )
  }

  if (!permissions['TESORERIA.VER']) {
    return <p className="text-sm text-destructive">No tiene permiso para ver tesorería.</p>
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Cartera</h2>
        <p className="text-sm text-muted-foreground">Seguimiento operativo de cuentas por cobrar y pagar.</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {renderAgingCard('Antiguedad de saldos CxC', agingCxc)}
        {renderAgingCard('Antiguedad de saldos CxP', agingCxp)}
      </div>

      {paymentState.id ? (
        <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-3" onSubmit={applyPayment}>
          <label className="text-sm">
            Monto
            <input
              type="number"
              min="0"
              step="1"
              inputMode="numeric"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={paymentState.monto}
              onChange={(event) => setPaymentState((prev) => ({ ...prev, monto: toIntegerString(event.target.value) }))}
              required
            />
            <span className="mt-1 block text-xs text-muted-foreground">{formatCurrencyCLP(paymentState.monto || 0)}</span>
          </label>
          <label className="text-sm">
            Fecha pago
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={paymentState.fecha_pago} onChange={(event) => setPaymentState((prev) => ({ ...prev, fecha_pago: event.target.value }))} required />
          </label>
          <div className="flex items-end gap-2">
            <Button type="submit">Confirmar</Button>
            <Button type="button" variant="outline" onClick={() => setPaymentState({ id: '', type: '', monto: '', fecha_pago: '' })}>Cancelar</Button>
          </div>
        </form>
      ) : null}

      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Cuentas por cobrar</h3>
        {renderTable(cxc, 'cxc')}
      </div>

      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Cuentas por pagar</h3>
        {renderTable(cxp, 'cxp')}
      </div>
    </section>
  )
}

export default TesoreriaCuentasPage
