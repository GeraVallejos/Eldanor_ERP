import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
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

function TesoreriaMonedasPage() {
  const canManage = usePermission('TESORERIA.CONCILIAR')
  const [monedas, setMonedas] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    codigo: 'CLP',
    nombre: 'Peso chileno',
    simbolo: '$',
    decimales: 0,
    tasa_referencia: 1,
    es_base: true,
    activa: true,
  })

  const loadMonedas = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/monedas/', { suppressGlobalErrorToast: true })
      setMonedas(normalizeListResponse(data))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las monedas.' }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadMonedas()
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await api.post('/monedas/', form, { suppressGlobalErrorToast: true })
      toast.success('Moneda creada correctamente.')
      setForm({
        codigo: '',
        nombre: '',
        simbolo: '',
        decimales: 2,
        tasa_referencia: 1,
        es_base: false,
        activa: true,
      })
      await loadMonedas()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la moneda.' }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Monedas</h2>
        <p className="text-sm text-muted-foreground">Catálogo base para tesorería, pricing y multimoneda.</p>
      </div>

      {canManage ? (
        <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-3" onSubmit={handleSubmit}>
          <label className="text-sm">
            Código
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.codigo}
              onChange={(event) => setForm((prev) => ({ ...prev, codigo: event.target.value.toUpperCase() }))}
              maxLength={3}
              required
            />
          </label>
          <label className="text-sm">
            Nombre
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.nombre}
              onChange={(event) => setForm((prev) => ({ ...prev, nombre: event.target.value }))}
              required
            />
          </label>
          <label className="text-sm">
            Símbolo
            <input
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.simbolo}
              onChange={(event) => setForm((prev) => ({ ...prev, simbolo: event.target.value }))}
            />
          </label>
          <label className="text-sm">
            Decimales
            <input
              type="number"
              min="0"
              max="6"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.decimales}
              onChange={(event) => setForm((prev) => ({ ...prev, decimales: Number(event.target.value || 0) }))}
            />
          </label>
          <label className="text-sm">
            Tasa referencia
            <input
              type="number"
              min="0.000001"
              step="0.000001"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.tasa_referencia}
              onChange={(event) => setForm((prev) => ({ ...prev, tasa_referencia: Number(event.target.value || 0) }))}
            />
          </label>
          <div className="flex flex-wrap items-end gap-4">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.es_base} onChange={(event) => setForm((prev) => ({ ...prev, es_base: event.target.checked }))} />
              Moneda base
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.activa} onChange={(event) => setForm((prev) => ({ ...prev, activa: event.target.checked }))} />
              Activa
            </label>
            <Button type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Agregar moneda'}</Button>
          </div>
        </form>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Código</th>
              <th className="px-3 py-2 text-left font-medium">Nombre</th>
              <th className="px-3 py-2 text-left font-medium">Símbolo</th>
              <th className="px-3 py-2 text-left font-medium">Decimales</th>
              <th className="px-3 py-2 text-left font-medium">Base</th>
              <th className="px-3 py-2 text-left font-medium">Activa</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>Cargando monedas...</td></tr>
            ) : monedas.length === 0 ? (
              <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>No hay monedas registradas.</td></tr>
            ) : (
              monedas.map((moneda) => (
                <tr key={moneda.id} className="border-t border-border">
                  <td className="px-3 py-2">{moneda.codigo}</td>
                  <td className="px-3 py-2">{moneda.nombre}</td>
                  <td className="px-3 py-2">{moneda.simbolo || '-'}</td>
                  <td className="px-3 py-2">{moneda.decimales}</td>
                  <td className="px-3 py-2">{moneda.es_base ? 'Sí' : 'No'}</td>
                  <td className="px-3 py-2">{moneda.activa ? 'Sí' : 'No'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default TesoreriaMonedasPage
