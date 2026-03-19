import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { formatSmartNumber, normalizeNumericInputByField } from '@/lib/numberFormat'
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

function TesoreriaTipoCambioPage() {
  const canManage = usePermission('TESORERIA.CONCILIAR')
  const [tiposCambio, setTiposCambio] = useState([])
  const [monedas, setMonedas] = useState([])
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    moneda_origen: '',
    moneda_destino: '',
    fecha: '',
    tasa: '',
    observacion: '',
  })

  const loadData = async () => {
    try {
      const [{ data: monedasData }, { data: cambiosData }] = await Promise.all([
        api.get('/monedas/', { suppressGlobalErrorToast: true }),
        api.get('/tipos-cambio/', { suppressGlobalErrorToast: true }),
      ])
      setMonedas(normalizeListResponse(monedasData))
      setTiposCambio(normalizeListResponse(cambiosData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los tipos de cambio.' }))
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const monedaLabel = (id) => {
    const moneda = monedas.find((item) => String(item.id) === String(id))
    return moneda ? `${moneda.codigo} - ${moneda.nombre}` : id
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await api.post('/tipos-cambio/', form, { suppressGlobalErrorToast: true })
      toast.success('Tipo de cambio registrado.')
      setForm({
        moneda_origen: '',
        moneda_destino: '',
        fecha: '',
        tasa: '',
        observacion: '',
      })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo registrar el tipo de cambio.' }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Tipos de cambio</h2>
        <p className="text-sm text-muted-foreground">Histórico de conversión para tesorería y precios multimoneda.</p>
      </div>

      {canManage ? (
        <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-5" onSubmit={handleSubmit}>
          <label className="text-sm">
            Moneda origen
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.moneda_origen} onChange={(event) => setForm((prev) => ({ ...prev, moneda_origen: event.target.value }))} required>
              <option value="">Seleccione</option>
              {monedas.map((moneda) => <option key={moneda.id} value={moneda.id}>{moneda.codigo}</option>)}
            </select>
          </label>
          <label className="text-sm">
            Moneda destino
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.moneda_destino} onChange={(event) => setForm((prev) => ({ ...prev, moneda_destino: event.target.value }))} required>
              <option value="">Seleccione</option>
              {monedas.map((moneda) => <option key={moneda.id} value={moneda.id}>{moneda.codigo}</option>)}
            </select>
          </label>
          <label className="text-sm">
            Fecha
            <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.fecha} onChange={(event) => setForm((prev) => ({ ...prev, fecha: event.target.value }))} required />
          </label>
          <label className="text-sm">
            Tasa
            <input
              type="number"
              min="0.000001"
              step="0.000001"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.tasa}
              onChange={(event) => setForm((prev) => ({ ...prev, tasa: normalizeNumericInputByField('tasa', event.target.value) }))}
              required
            />
            <span className="mt-1 block text-xs text-muted-foreground">{formatSmartNumber(form.tasa || 0, { maximumFractionDigits: 6 })}</span>
          </label>
          <div className="flex items-end">
            <Button type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Registrar'}</Button>
          </div>
          <label className="text-sm md:col-span-5">
            Observación
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.observacion} onChange={(event) => setForm((prev) => ({ ...prev, observacion: event.target.value }))} />
          </label>
        </form>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Fecha</th>
              <th className="px-3 py-2 text-left font-medium">Origen</th>
              <th className="px-3 py-2 text-left font-medium">Destino</th>
              <th className="px-3 py-2 text-left font-medium">Tasa</th>
              <th className="px-3 py-2 text-left font-medium">Observación</th>
            </tr>
          </thead>
          <tbody>
            {tiposCambio.length === 0 ? (
              <tr><td className="px-3 py-3 text-muted-foreground" colSpan={5}>No hay tipos de cambio registrados.</td></tr>
            ) : (
              tiposCambio.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="px-3 py-2">{item.fecha}</td>
                  <td className="px-3 py-2">{monedaLabel(item.moneda_origen)}</td>
                  <td className="px-3 py-2">{monedaLabel(item.moneda_destino)}</td>
                  <td className="px-3 py-2">{formatSmartNumber(item.tasa, { maximumFractionDigits: 6 })}</td>
                  <td className="px-3 py-2">{item.observacion || '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default TesoreriaTipoCambioPage
