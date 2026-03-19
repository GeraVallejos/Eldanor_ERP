import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import { formatCurrencyCLP, toIntegerString } from '@/lib/numberFormat'
import { usePermission } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }
  if (Array.isArray(data?.results)) {
    return data.results
  }
  return []
}

function formatCuentaLabel(cuenta) {
  return `${cuenta.alias || 'Sin alias'}${cuenta.numero_cuenta ? ` · ${cuenta.numero_cuenta}` : ''}`
}

function formatEstadoContable(value) {
  const mapping = {
    NO_APLICA: 'No aplica',
    PENDIENTE: 'Pendiente',
    CONTABILIZADO: 'Contabilizado',
    ERROR: 'Error',
  }
  return mapping[value] || value || '-'
}

function TesoreriaBancosPage() {
  const canView = usePermission('TESORERIA.VER')
  const canConciliar = usePermission('TESORERIA.CONCILIAR')
  const [loading, setLoading] = useState(true)
  const [savingCuenta, setSavingCuenta] = useState(false)
  const [conciliando, setConciliando] = useState(false)
  const [cuentas, setCuentas] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [cxc, setCxc] = useState([])
  const [cxp, setCxp] = useState([])
  const [monedas, setMonedas] = useState([])
  const [selectedCuenta, setSelectedCuenta] = useState('')
  const [showOnlyPendientes, setShowOnlyPendientes] = useState(true)
  const [cuentaForm, setCuentaForm] = useState({
    alias: '',
    banco: '',
    tipo_cuenta: 'CORRIENTE',
    numero_cuenta: '',
    titular: '',
    moneda: '',
    saldo_referencial: '0',
    activa: true,
  })
  const [conciliacion, setConciliacion] = useState({
    movimientoId: '',
    tipoCuenta: 'cxc',
    cuentaId: '',
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [
        { data: cuentasData },
        { data: movimientosData },
        { data: cxcData },
        { data: cxpData },
        { data: monedasData },
      ] = await Promise.all([
        api.get('/cuentas-bancarias/', { suppressGlobalErrorToast: true }),
        api.get('/movimientos-bancarios/', { suppressGlobalErrorToast: true }),
        api.get('/cuentas-por-cobrar/', { suppressGlobalErrorToast: true }),
        api.get('/cuentas-por-pagar/', { suppressGlobalErrorToast: true }),
        api.get('/monedas/', { suppressGlobalErrorToast: true }),
      ])

      const cuentasNormalizadas = normalizeListResponse(cuentasData)
      setCuentas(cuentasNormalizadas)
      setMovimientos(normalizeListResponse(movimientosData))
      setCxc(normalizeListResponse(cxcData))
      setCxp(normalizeListResponse(cxpData))
      setMonedas(normalizeListResponse(monedasData))

      setSelectedCuenta((current) => current || String(cuentasNormalizadas[0]?.id || ''))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la operacion bancaria.' }))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!canView) {
      return
    }
    void loadData()
  }, [canView, loadData])

  const monedaById = useMemo(() => {
    const map = new Map()
    monedas.forEach((moneda) => {
      map.set(String(moneda.id), moneda)
    })
    return map
  }, [monedas])

  const cuentaById = useMemo(() => {
    const map = new Map()
    cuentas.forEach((cuenta) => {
      map.set(String(cuenta.id), cuenta)
    })
    return map
  }, [cuentas])

  const movimientosFiltrados = useMemo(() => {
    return movimientos
      .filter((movimiento) => !selectedCuenta || String(movimiento.cuenta_bancaria) === String(selectedCuenta))
      .filter((movimiento) => !showOnlyPendientes || !movimiento.conciliado)
      .sort((left, right) => String(right.fecha).localeCompare(String(left.fecha)))
  }, [movimientos, selectedCuenta, showOnlyPendientes])

  const cxcPendientes = useMemo(() => cxc.filter((item) => item.estado !== 'PAGADA' && item.estado !== 'ANULADA'), [cxc])
  const cxpPendientes = useMemo(() => cxp.filter((item) => item.estado !== 'PAGADA' && item.estado !== 'ANULADA'), [cxp])

  const cuentasActivas = cuentas.filter((item) => item.activa)
  const movimientosPendientes = movimientos.filter((item) => !item.conciliado)
  const movimientosConciliados = movimientos.filter((item) => item.conciliado)
  const saldoReferencial = cuentas.reduce((acc, cuenta) => acc + Number(cuenta.saldo_referencial || 0), 0)

  const handleCuentaSubmit = async (event) => {
    event.preventDefault()
    setSavingCuenta(true)
    try {
      await api.post('/cuentas-bancarias/', cuentaForm, { suppressGlobalErrorToast: true })
      toast.success('Cuenta bancaria creada correctamente.')
      setCuentaForm({
        alias: '',
        banco: '',
        tipo_cuenta: 'CORRIENTE',
        numero_cuenta: '',
        titular: '',
        moneda: '',
        saldo_referencial: '0',
        activa: true,
      })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la cuenta bancaria.' }))
    } finally {
      setSavingCuenta(false)
    }
  }

  const handleConciliar = async (event) => {
    event.preventDefault()
    if (!conciliacion.movimientoId || !conciliacion.cuentaId) {
      return
    }

    setConciliando(true)
    try {
      const payload = conciliacion.tipoCuenta === 'cxc'
        ? { cuenta_por_cobrar: conciliacion.cuentaId }
        : { cuenta_por_pagar: conciliacion.cuentaId }

      await api.post(`/movimientos-bancarios/${conciliacion.movimientoId}/conciliar/`, payload, { suppressGlobalErrorToast: true })
      toast.success('Movimiento conciliado correctamente.')
      setConciliacion({ movimientoId: '', tipoCuenta: 'cxc', cuentaId: '' })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo conciliar el movimiento.' }))
    } finally {
      setConciliando(false)
    }
  }

  const cuentasDisponibles = conciliacion.tipoCuenta === 'cxc' ? cxcPendientes : cxpPendientes

  if (!canView) {
    return <p className="text-sm text-destructive">No tiene permiso para ver tesoreria bancaria.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Bancos y conciliacion</h2>
          <p className="text-sm text-muted-foreground">Operacion diaria de cuentas bancarias, cartolas importadas y conciliacion con cartera.</p>
        </div>
        {canConciliar ? (
          <BulkImportButton endpoint="/movimientos-bancarios/bulk_import/" templateEndpoint="/movimientos-bancarios/bulk_template/" onCompleted={() => { void loadData() }} />
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Cuentas activas</p>
          <p className="mt-2 text-2xl font-semibold">{cuentasActivas.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Bancos propios disponibles para operar.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Pendientes por conciliar</p>
          <p className="mt-2 text-2xl font-semibold">{movimientosPendientes.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Movimientos listos para revision operativa.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Conciliados</p>
          <p className="mt-2 text-2xl font-semibold">{movimientosConciliados.length}</p>
          <p className="mt-1 text-xs text-muted-foreground">Trazabilidad lista para futura contabilidad.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Saldo referencial</p>
          <p className="mt-2 text-2xl font-semibold">{formatCurrencyCLP(saldoReferencial)}</p>
          <p className="mt-1 text-xs text-muted-foreground">Referencia interna para seguimiento de caja y banco.</p>
        </div>
      </div>

      {canConciliar ? (
        <form className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-2 xl:grid-cols-7" onSubmit={handleCuentaSubmit}>
          <label className="text-sm xl:col-span-2">
            Alias
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.alias} onChange={(event) => setCuentaForm((prev) => ({ ...prev, alias: event.target.value }))} required />
          </label>
          <label className="text-sm xl:col-span-2">
            Banco
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.banco} onChange={(event) => setCuentaForm((prev) => ({ ...prev, banco: event.target.value }))} required />
          </label>
          <label className="text-sm">
            Tipo
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.tipo_cuenta} onChange={(event) => setCuentaForm((prev) => ({ ...prev, tipo_cuenta: event.target.value }))}>
              <option value="CORRIENTE">Corriente</option>
              <option value="VISTA">Vista</option>
              <option value="AHORRO">Ahorro</option>
            </select>
          </label>
          <label className="text-sm">
            Nro. cuenta
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.numero_cuenta} onChange={(event) => setCuentaForm((prev) => ({ ...prev, numero_cuenta: event.target.value }))} required />
          </label>
          <label className="text-sm">
            Moneda
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.moneda} onChange={(event) => setCuentaForm((prev) => ({ ...prev, moneda: event.target.value }))} required>
              <option value="">Seleccione</option>
              {monedas.map((moneda) => <option key={moneda.id} value={moneda.id}>{moneda.codigo}</option>)}
            </select>
          </label>
          <label className="text-sm xl:col-span-2">
            Titular
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.titular} onChange={(event) => setCuentaForm((prev) => ({ ...prev, titular: event.target.value }))} required />
          </label>
          <label className="text-sm">
            Saldo referencial
            <input type="number" min="0" step="1" inputMode="numeric" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={cuentaForm.saldo_referencial} onChange={(event) => setCuentaForm((prev) => ({ ...prev, saldo_referencial: toIntegerString(event.target.value) }))} />
            <span className="mt-1 block text-xs text-muted-foreground">{formatCurrencyCLP(cuentaForm.saldo_referencial || 0)}</span>
          </label>
          <label className="inline-flex items-center gap-2 self-end text-sm">
            <input type="checkbox" checked={cuentaForm.activa} onChange={(event) => setCuentaForm((prev) => ({ ...prev, activa: event.target.checked }))} />
            Activa
          </label>
          <div className="flex items-end">
            <Button type="submit" disabled={savingCuenta}>{savingCuenta ? 'Guardando...' : 'Agregar cuenta'}</Button>
          </div>
        </form>
      ) : null}

      {conciliacion.movimientoId ? (
        <form className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-4" onSubmit={handleConciliar}>
          <label className="text-sm">
            Tipo de cuenta
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={conciliacion.tipoCuenta} onChange={(event) => setConciliacion((prev) => ({ ...prev, tipoCuenta: event.target.value, cuentaId: '' }))}>
              <option value="cxc">Cuenta por cobrar</option>
              <option value="cxp">Cuenta por pagar</option>
            </select>
          </label>
          <label className="text-sm md:col-span-2">
            Documento a conciliar
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={conciliacion.cuentaId} onChange={(event) => setConciliacion((prev) => ({ ...prev, cuentaId: event.target.value }))} required>
              <option value="">Seleccione</option>
              {cuentasDisponibles.map((item) => <option key={item.id} value={item.id}>{item.referencia} · saldo {formatCurrencyCLP(item.saldo)}</option>)}
            </select>
          </label>
          <div className="flex items-end gap-2">
            <Button type="submit" disabled={conciliando}>{conciliando ? 'Conciliando...' : 'Confirmar'}</Button>
            <Button type="button" variant="outline" onClick={() => setConciliacion({ movimientoId: '', tipoCuenta: 'cxc', cuentaId: '' })}>Cancelar</Button>
          </div>
        </form>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-lg font-semibold">Cuentas bancarias</h3>
            <span className="text-xs text-muted-foreground">{cuentas.length} registradas</span>
          </div>
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando cuentas...</p>
          ) : cuentas.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aun no hay cuentas bancarias creadas.</p>
          ) : (
            <div className="space-y-2">
              {cuentas.map((cuenta) => {
                const moneda = monedaById.get(String(cuenta.moneda))
                const isSelected = String(selectedCuenta) === String(cuenta.id)
                return (
                  <button key={cuenta.id} type="button" onClick={() => setSelectedCuenta(String(cuenta.id))} className={`w-full rounded-lg border px-3 py-3 text-left transition ${isSelected ? 'border-primary bg-primary/5' : 'border-border bg-background hover:border-primary/40'}`}>
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{cuenta.alias}</p>
                      <span className="text-xs text-muted-foreground">{cuenta.activa ? 'Activa' : 'Inactiva'}</span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{cuenta.banco} · {cuenta.numero_cuenta}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{moneda?.codigo || 'MON'} · saldo ref. {formatCurrencyCLP(cuenta.saldo_referencial)}</p>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h3 className="text-lg font-semibold">Movimientos bancarios</h3>
              <p className="text-sm text-muted-foreground">Revision simple de cartola y conciliacion.</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                <input type="checkbox" checked={showOnlyPendientes} onChange={(event) => setShowOnlyPendientes(event.target.checked)} />
                Mostrar solo pendientes
              </label>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Fecha</th>
                  <th className="px-3 py-2 text-left font-medium">Cuenta</th>
                  <th className="px-3 py-2 text-left font-medium">Tipo</th>
                  <th className="px-3 py-2 text-left font-medium">Referencia</th>
                  <th className="px-3 py-2 text-left font-medium">Monto</th>
                  <th className="px-3 py-2 text-left font-medium">Estado</th>
                  <th className="px-3 py-2 text-left font-medium">Estado contable</th>
                  <th className="px-3 py-2 text-left font-medium">Accion</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={8}>Cargando movimientos...</td></tr>
                ) : movimientosFiltrados.length === 0 ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={8}>No hay movimientos para los filtros seleccionados.</td></tr>
                ) : (
                  movimientosFiltrados.map((movimiento) => {
                    const cuenta = cuentaById.get(String(movimiento.cuenta_bancaria))
                    return (
                      <tr key={movimiento.id} className="border-t border-border">
                        <td className="px-3 py-2">{movimiento.fecha}</td>
                        <td className="px-3 py-2">{cuenta ? formatCuentaLabel(cuenta) : movimiento.cuenta_bancaria}</td>
                        <td className="px-3 py-2">{movimiento.tipo}</td>
                        <td className="px-3 py-2">{movimiento.referencia || '-'}</td>
                        <td className="px-3 py-2">{formatCurrencyCLP(movimiento.monto)}</td>
                        <td className="px-3 py-2">{movimiento.conciliado ? 'Conciliado' : 'Pendiente'}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{formatEstadoContable(movimiento.estado_contable)}</td>
                        <td className="px-3 py-2">
                          {movimiento.conciliado || !canConciliar ? (
                            <span className="text-xs text-muted-foreground">{movimiento.conciliado ? 'Listo' : 'Sin permiso'}</span>
                          ) : (
                            <Button size="sm" variant="outline" className="h-8 px-2 text-xs" onClick={() => setConciliacion({ movimientoId: movimiento.id, tipoCuenta: 'cxc', cuentaId: '' })}>
                              Conciliar
                            </Button>
                          )}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}

export default TesoreriaBancosPage
