import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { formatCurrencyCLP } from '@/lib/numberFormat'
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

function ContabilidadReportesPage() {
  const canView = usePermission('CONTABILIDAD.VER')
  const [loading, setLoading] = useState(true)
  const [filtros, setFiltros] = useState({ fecha_desde: '', fecha_hasta: '' })
  const [balance, setBalance] = useState([])
  const [libroMayor, setLibroMayor] = useState([])
  const [estadoResultados, setEstadoResultados] = useState({
    ingresos: [],
    gastos: [],
    total_ingresos: 0,
    total_gastos: 0,
    utilidad: 0,
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filtros.fecha_desde) {
        params.fecha_desde = filtros.fecha_desde
      }
      if (filtros.fecha_hasta) {
        params.fecha_hasta = filtros.fecha_hasta
      }
      const [{ data: balanceData }, { data: resultadosData }, { data: mayorData }] = await Promise.all([
        api.get('/asientos-contables/balance_comprobacion/', { params, suppressGlobalErrorToast: true }),
        api.get('/asientos-contables/estado_resultados/', { params, suppressGlobalErrorToast: true }),
        api.get('/asientos-contables/libro_mayor/', { params, suppressGlobalErrorToast: true }),
      ])
      setBalance(normalizeListResponse(balanceData))
      setLibroMayor(normalizeListResponse(mayorData))
      setEstadoResultados(resultadosData || {
        ingresos: [],
        gastos: [],
        total_ingresos: 0,
        total_gastos: 0,
        utilidad: 0,
      })
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los reportes contables.' }))
    } finally {
      setLoading(false)
    }
  }, [filtros])

  useEffect(() => {
    if (!canView) {
      return
    }
    void loadData()
  }, [canView, loadData])

  const topMayores = useMemo(() => libroMayor.slice(0, 8), [libroMayor])

  if (!canView) {
    return <p className="text-sm text-destructive">No tiene permiso para revisar reportes contables.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Reportes contables</h2>
          <p className="text-sm text-muted-foreground">
            Balance de comprobacion, libro mayor resumido y estado de resultados sobre asientos contabilizados.
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <input
            type="date"
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={filtros.fecha_desde}
            onChange={(event) => setFiltros((prev) => ({ ...prev, fecha_desde: event.target.value }))}
          />
          <input
            type="date"
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={filtros.fecha_hasta}
            onChange={(event) => setFiltros((prev) => ({ ...prev, fecha_hasta: event.target.value }))}
          />
          <Button type="button" variant="outline" onClick={() => { void loadData() }}>Actualizar</Button>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Ingresos</p>
          <p className="mt-2 text-2xl font-semibold">{formatCurrencyCLP(estadoResultados.total_ingresos || 0)}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Gastos</p>
          <p className="mt-2 text-2xl font-semibold">{formatCurrencyCLP(estadoResultados.total_gastos || 0)}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Utilidad</p>
          <p className="mt-2 text-2xl font-semibold">{formatCurrencyCLP(estadoResultados.utilidad || 0)}</p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(380px,0.9fr)]">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Balance de comprobacion</h3>
            <p className="text-sm text-muted-foreground">Resumen por cuenta con debe, haber y saldo para revision de cuadratura.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Cuenta</th>
                  <th className="px-3 py-2 text-right font-medium">Debe</th>
                  <th className="px-3 py-2 text-right font-medium">Haber</th>
                  <th className="px-3 py-2 text-right font-medium">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={4}>Cargando reporte...</td></tr>
                ) : balance.length === 0 ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={4}>Sin movimientos para el rango seleccionado.</td></tr>
                ) : (
                  balance.map((item) => (
                    <tr key={item.cuenta_id} className="border-t border-border">
                      <td className="px-3 py-2">{item.codigo} - {item.nombre}</td>
                      <td className="px-3 py-2 text-right">{formatCurrencyCLP(item.debe)}</td>
                      <td className="px-3 py-2 text-right">{formatCurrencyCLP(item.haber)}</td>
                      <td className="px-3 py-2 text-right">{formatCurrencyCLP(item.saldo)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3">
              <h3 className="text-lg font-semibold">Libro mayor resumido</h3>
              <p className="text-sm text-muted-foreground">Top de cuentas con movimiento para una lectura rapida del periodo.</p>
            </div>
            <div className="space-y-3">
              {loading ? (
                <p className="text-sm text-muted-foreground">Cargando libro mayor...</p>
              ) : topMayores.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin movimientos para mostrar.</p>
              ) : (
                topMayores.map((item) => (
                  <article key={item.cuenta_id} className="rounded-lg border border-border p-3">
                    <p className="font-medium">{item.codigo} - {item.nombre}</p>
                    <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
                      <span>Debe: {formatCurrencyCLP(item.debe)}</span>
                      <span>Haber: {formatCurrencyCLP(item.haber)}</span>
                      <span>Saldo: {formatCurrencyCLP(item.saldo)}</span>
                    </div>
                  </article>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="mb-3">
              <h3 className="text-lg font-semibold">Detalle estado de resultados</h3>
              <p className="text-sm text-muted-foreground">Desglose de cuentas de ingreso y gasto ya contabilizadas.</p>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium">Ingresos</p>
                <div className="mt-2 space-y-2">
                  {loading ? (
                    <p className="text-sm text-muted-foreground">Cargando ingresos...</p>
                  ) : estadoResultados.ingresos?.length ? (
                    estadoResultados.ingresos.map((item) => (
                      <div key={item.cuenta_id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm">
                        <span>{item.codigo} - {item.nombre}</span>
                        <span className="font-medium">{formatCurrencyCLP(item.haber)}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">Sin ingresos en el rango.</p>
                  )}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium">Gastos</p>
                <div className="mt-2 space-y-2">
                  {loading ? (
                    <p className="text-sm text-muted-foreground">Cargando gastos...</p>
                  ) : estadoResultados.gastos?.length ? (
                    estadoResultados.gastos.map((item) => (
                      <div key={item.cuenta_id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm">
                        <span>{item.codigo} - {item.nombre}</span>
                        <span className="font-medium">{formatCurrencyCLP(item.debe)}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">Sin gastos en el rango.</p>
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

export default ContabilidadReportesPage
