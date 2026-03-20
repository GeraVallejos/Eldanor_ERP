import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
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

function buildEmptyRow() {
  return { cuenta: '', glosa: '', debe: '', haber: '' }
}

function ContabilidadAsientosPage() {
  const canView = usePermission('CONTABILIDAD.VER')
  const canManage = usePermission('CONTABILIDAD.CONTABILIZAR')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [reprocessing, setReprocessing] = useState(false)
  const [contabilizandoId, setContabilizandoId] = useState('')
  const [cuentas, setCuentas] = useState([])
  const [asientos, setAsientos] = useState([])
  const [errores, setErrores] = useState([])
  const [form, setForm] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    glosa: '',
    movimientos_data: [buildEmptyRow(), buildEmptyRow()],
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const requests = [
        api.get('/plan-cuentas/', { suppressGlobalErrorToast: true }),
        api.get('/asientos-contables/', { suppressGlobalErrorToast: true }),
      ]
      if (canManage) {
        requests.push(api.get('/asientos-contables/errores/', { suppressGlobalErrorToast: true }))
      }

      const responses = await Promise.all(requests)
      const cuentasList = normalizeListResponse(responses[0].data)
      setCuentas(cuentasList.filter((item) => item.activa && item.acepta_movimientos))
      setAsientos(normalizeListResponse(responses[1].data))
      setErrores(canManage ? normalizeListResponse(responses[2]?.data) : [])
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la informacion contable.' }))
    } finally {
      setLoading(false)
    }
  }, [canManage])

  useEffect(() => {
    if (!canView) {
      return
    }
    void loadData()
  }, [canView, loadData])

  const stats = useMemo(() => ({
    borradores: asientos.filter((item) => item.estado === 'BORRADOR').length,
    contabilizados: asientos.filter((item) => item.estado === 'CONTABILIZADO').length,
    integraciones: asientos.filter((item) => item.origen === 'INTEGRACION').length,
    errores: errores.length,
  }), [asientos, errores])

  const rows = form.movimientos_data
  const totalDebe = rows.reduce((acc, item) => acc + Number(item.debe || 0), 0)
  const totalHaber = rows.reduce((acc, item) => acc + Number(item.haber || 0), 0)
  const cuadrado = totalDebe > 0 && totalDebe === totalHaber

  const handleRowChange = (index, field, value) => {
    setForm((prev) => ({
      ...prev,
      movimientos_data: prev.movimientos_data.map((item, currentIndex) => {
        if (currentIndex !== index) {
          return item
        }
        if (field === 'debe' || field === 'haber') {
          return { ...item, [field]: toIntegerString(value) }
        }
        return { ...item, [field]: value }
      }),
    }))
  }

  const addRow = () => {
    setForm((prev) => ({
      ...prev,
      movimientos_data: [...prev.movimientos_data, buildEmptyRow()],
    }))
  }

  const removeRow = (index) => {
    setForm((prev) => ({
      ...prev,
      movimientos_data: prev.movimientos_data.filter((_, currentIndex) => currentIndex !== index),
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await api.post('/asientos-contables/', form, { suppressGlobalErrorToast: true })
      toast.success('Asiento creado en borrador.')
      setForm({
        fecha: new Date().toISOString().slice(0, 10),
        glosa: '',
        movimientos_data: [buildEmptyRow(), buildEmptyRow()],
      })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear el asiento.' }))
    } finally {
      setSaving(false)
    }
  }

  const handleProcesar = async () => {
    setProcessing(true)
    try {
      const { data } = await api.post('/asientos-contables/procesar_solicitudes/', {}, { suppressGlobalErrorToast: true })
      toast.success(`Solicitudes procesadas: ${data.processed || 0}.`)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron procesar las solicitudes.' }))
    } finally {
      setProcessing(false)
    }
  }

  const handleReprocesar = async () => {
    setReprocessing(true)
    try {
      const { data } = await api.post('/asientos-contables/reprocesar_errores/', {}, { suppressGlobalErrorToast: true })
      toast.success(`Errores reenviados: ${data.processed || 0}.`)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron reprocesar los errores contables.' }))
    } finally {
      setReprocessing(false)
    }
  }

  const handleContabilizar = async (asientoId) => {
    setContabilizandoId(asientoId)
    try {
      await api.post(`/asientos-contables/${asientoId}/contabilizar/`, {}, { suppressGlobalErrorToast: true })
      toast.success('Asiento contabilizado.')
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo contabilizar el asiento.' }))
    } finally {
      setContabilizandoId('')
    }
  }

  if (!canView) {
    return <p className="text-sm text-destructive">No tiene permiso para revisar asientos contables.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Asientos, centralizacion y excepciones</h2>
          <p className="text-sm text-muted-foreground">
            Panel contable para ingreso manual, contabilizacion, procesamiento de integraciones y control de fallos pendientes.
          </p>
        </div>
        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={handleReprocesar} disabled={reprocessing || errores.length === 0}>
              {reprocessing ? 'Reprocesando...' : 'Reprocesar errores'}
            </Button>
            <Button type="button" onClick={handleProcesar} disabled={processing}>
              {processing ? 'Procesando...' : 'Procesar solicitudes'}
            </Button>
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Borradores</p>
          <p className="mt-2 text-2xl font-semibold">{stats.borradores}</p>
          <p className="mt-1 text-xs text-muted-foreground">Asientos pendientes de revisar o contabilizar.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Contabilizados</p>
          <p className="mt-2 text-2xl font-semibold">{stats.contabilizados}</p>
          <p className="mt-1 text-xs text-muted-foreground">Impacto confirmado en la contabilidad.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Integraciones</p>
          <p className="mt-2 text-2xl font-semibold">{stats.integraciones}</p>
          <p className="mt-1 text-xs text-muted-foreground">Asientos generados desde ventas, compras o tesoreria.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Errores pendientes</p>
          <p className="mt-2 text-2xl font-semibold">{stats.errores}</p>
          <p className="mt-1 text-xs text-muted-foreground">Solicitudes contables con fallo listo para reproceso.</p>
        </div>
      </div>

      {canManage ? (
        <form className="space-y-4 rounded-xl border border-border bg-card p-4" onSubmit={handleSubmit}>
          <div>
            <h3 className="text-lg font-semibold">Ingreso manual de asiento</h3>
            <p className="text-sm text-muted-foreground">Pensado para ajustes, aperturas, regularizaciones y reclasificaciones contables.</p>
          </div>

          <div className="grid gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
            <label className="text-sm">
              Fecha
              <input
                type="date"
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                value={form.fecha}
                onChange={(event) => setForm((prev) => ({ ...prev, fecha: event.target.value }))}
                required
              />
            </label>
            <label className="text-sm">
              Glosa
              <input
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                value={form.glosa}
                onChange={(event) => setForm((prev) => ({ ...prev, glosa: event.target.value }))}
                placeholder="Ejemplo: reclasificacion de gastos operativos"
                required
              />
            </label>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Cuenta</th>
                  <th className="px-3 py-2 text-left font-medium">Glosa</th>
                  <th className="px-3 py-2 text-left font-medium">Debe</th>
                  <th className="px-3 py-2 text-left font-medium">Haber</th>
                  <th className="px-3 py-2 text-left font-medium">Accion</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={`row-${index}`} className="border-t border-border">
                    <td className="px-3 py-2">
                      <select
                        className="w-full rounded-md border border-input bg-background px-3 py-2"
                        value={row.cuenta}
                        onChange={(event) => handleRowChange(index, 'cuenta', event.target.value)}
                        required
                      >
                        <option value="">Seleccione</option>
                        {cuentas.map((cuenta) => (
                          <option key={cuenta.id} value={cuenta.id}>
                            {cuenta.codigo} - {cuenta.nombre}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="w-full rounded-md border border-input bg-background px-3 py-2"
                        value={row.glosa}
                        onChange={(event) => handleRowChange(index, 'glosa', event.target.value)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        className="w-full rounded-md border border-input bg-background px-3 py-2"
                        value={row.debe}
                        onChange={(event) => handleRowChange(index, 'debe', event.target.value)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        className="w-full rounded-md border border-input bg-background px-3 py-2"
                        value={row.haber}
                        onChange={(event) => handleRowChange(index, 'haber', event.target.value)}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <Button type="button" variant="outline" className="h-8 px-2 text-xs" onClick={() => removeRow(index)} disabled={rows.length <= 2}>
                        Quitar
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span>Debe: {formatCurrencyCLP(totalDebe)}</span>
              <span>Haber: {formatCurrencyCLP(totalHaber)}</span>
              <span className={cuadrado ? 'text-emerald-600' : 'text-amber-600'}>
                {cuadrado ? 'Asiento cuadrado' : 'Revise la cuadratura'}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={addRow}>Agregar linea</Button>
              <Button type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Guardar borrador'}</Button>
            </div>
          </div>
        </form>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.9fr)]">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Ultimos asientos</h3>
            <p className="text-sm text-muted-foreground">Revision de origen, montos y estado para control diario del libro.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Numero</th>
                  <th className="px-3 py-2 text-left font-medium">Fecha</th>
                  <th className="px-3 py-2 text-left font-medium">Glosa</th>
                  <th className="px-3 py-2 text-left font-medium">Origen</th>
                  <th className="px-3 py-2 text-left font-medium">Debe</th>
                  <th className="px-3 py-2 text-left font-medium">Haber</th>
                  <th className="px-3 py-2 text-left font-medium">Estado</th>
                  <th className="px-3 py-2 text-left font-medium">Accion</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={8}>Cargando asientos...</td></tr>
                ) : asientos.length === 0 ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={8}>Aun no hay asientos registrados.</td></tr>
                ) : (
                  asientos.map((asiento) => (
                    <tr key={asiento.id} className="border-t border-border">
                      <td className="px-3 py-2 font-medium">{asiento.numero}</td>
                      <td className="px-3 py-2">{asiento.fecha}</td>
                      <td className="px-3 py-2">{asiento.glosa}</td>
                      <td className="px-3 py-2">{asiento.origen}</td>
                      <td className="px-3 py-2">{formatCurrencyCLP(asiento.total_debe)}</td>
                      <td className="px-3 py-2">{formatCurrencyCLP(asiento.total_haber)}</td>
                      <td className="px-3 py-2">{asiento.estado}</td>
                      <td className="px-3 py-2">
                        {canManage && asiento.estado === 'BORRADOR' ? (
                          <Button
                            type="button"
                            variant="outline"
                            className="h-8 px-2 text-xs"
                            onClick={() => handleContabilizar(asiento.id)}
                            disabled={contabilizandoId === asiento.id}
                          >
                            {contabilizandoId === asiento.id ? 'Procesando...' : 'Contabilizar'}
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground">{asiento.estado === 'CONTABILIZADO' ? 'Listo' : '-'}</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold">Errores de integracion</h3>
              <p className="text-sm text-muted-foreground">Bandeja para revisar payloads fallidos, motivo y numero de intentos.</p>
            </div>
            {canManage ? (
              <Button type="button" variant="outline" className="shrink-0" onClick={handleReprocesar} disabled={reprocessing || errores.length === 0}>
                {reprocessing ? 'Reprocesando...' : 'Reintentar todo'}
              </Button>
            ) : null}
          </div>
          <div className="space-y-3">
            {loading ? (
              <p className="text-sm text-muted-foreground">Cargando errores...</p>
            ) : errores.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border px-3 py-4 text-sm text-muted-foreground">
                No hay errores contables pendientes.
              </p>
            ) : (
              errores.map((error) => (
                <article key={error.id} className="rounded-lg border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium">{error.aggregate_type} · {error.aggregate_id}</p>
                    <span className="text-xs text-muted-foreground">Intentos: {error.attempts}</span>
                  </div>
                  <p className="mt-2 text-sm">{error.glosa || 'Sin glosa informada.'}</p>
                  <p className="mt-2 text-sm text-destructive">{error.error || 'Sin detalle tecnico disponible.'}</p>
                  <p className="mt-2 text-xs text-muted-foreground">Disponible desde: {error.available_at}</p>
                </article>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export default ContabilidadAsientosPage
