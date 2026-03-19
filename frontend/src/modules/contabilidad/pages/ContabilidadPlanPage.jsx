import { useCallback, useEffect, useMemo, useState } from 'react'
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

function ContabilidadPlanPage() {
  const canView = usePermission('CONTABILIDAD.VER')
  const canManage = usePermission('CONTABILIDAD.CONTABILIZAR')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [cuentas, setCuentas] = useState([])
  const [form, setForm] = useState({
    codigo: '',
    nombre: '',
    tipo: 'ACTIVO',
    padre: '',
    acepta_movimientos: true,
    activa: true,
    descripcion: '',
  })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/plan-cuentas/', { suppressGlobalErrorToast: true })
      setCuentas(normalizeListResponse(data))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el plan de cuentas.' }))
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

  const cuentasPadre = useMemo(
    () => cuentas.filter((item) => item.acepta_movimientos === false && item.activa),
    [cuentas],
  )

  const stats = useMemo(() => ({
    total: cuentas.length,
    activas: cuentas.filter((item) => item.activa).length,
    imputables: cuentas.filter((item) => item.acepta_movimientos).length,
  }), [cuentas])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      const { data } = await api.post('/plan-cuentas/seed_base/', {}, { suppressGlobalErrorToast: true })
      toast.success(`Plan base sincronizado. ${data.created || 0} cuentas nuevas.`)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo inicializar el plan base.' }))
    } finally {
      setSeeding(false)
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      await api.post('/plan-cuentas/', {
        ...form,
        padre: form.padre || null,
      }, { suppressGlobalErrorToast: true })
      toast.success('Cuenta contable creada.')
      setForm({
        codigo: '',
        nombre: '',
        tipo: 'ACTIVO',
        padre: '',
        acepta_movimientos: true,
        activa: true,
        descripcion: '',
      })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la cuenta contable.' }))
    } finally {
      setSaving(false)
    }
  }

  if (!canView) {
    return <p className="text-sm text-destructive">No tiene permiso para revisar contabilidad.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Plan de cuentas</h2>
          <p className="text-sm text-muted-foreground">Base ordenada para contabilidad, con una vista simple para configuracion inicial y cuentas operativas.</p>
        </div>
        {canManage ? (
          <Button type="button" onClick={handleSeed} disabled={seeding}>
            {seeding ? 'Inicializando...' : 'Inicializar plan base'}
          </Button>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Cuentas totales</p>
          <p className="mt-2 text-2xl font-semibold">{stats.total}</p>
          <p className="mt-1 text-xs text-muted-foreground">Incluye cuentas de detalle y de agrupacion.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Activas</p>
          <p className="mt-2 text-2xl font-semibold">{stats.activas}</p>
          <p className="mt-1 text-xs text-muted-foreground">Disponibles para uso inmediato.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Imputables</p>
          <p className="mt-2 text-2xl font-semibold">{stats.imputables}</p>
          <p className="mt-1 text-xs text-muted-foreground">Aceptan movimientos directos en asientos.</p>
        </div>
      </div>

      {canManage ? (
        <form className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-2 xl:grid-cols-6" onSubmit={handleSubmit}>
          <label className="text-sm">
            Codigo
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.codigo} onChange={(event) => setForm((prev) => ({ ...prev, codigo: event.target.value.toUpperCase() }))} required />
          </label>
          <label className="text-sm xl:col-span-2">
            Nombre
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.nombre} onChange={(event) => setForm((prev) => ({ ...prev, nombre: event.target.value }))} required />
          </label>
          <label className="text-sm">
            Tipo
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.tipo} onChange={(event) => setForm((prev) => ({ ...prev, tipo: event.target.value }))}>
              <option value="ACTIVO">Activo</option>
              <option value="PASIVO">Pasivo</option>
              <option value="PATRIMONIO">Patrimonio</option>
              <option value="INGRESO">Ingreso</option>
              <option value="GASTO">Gasto</option>
            </select>
          </label>
          <label className="text-sm xl:col-span-2">
            Cuenta padre
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.padre} onChange={(event) => setForm((prev) => ({ ...prev, padre: event.target.value }))}>
              <option value="">Sin padre</option>
              {cuentasPadre.map((cuenta) => (
                <option key={cuenta.id} value={cuenta.id}>{cuenta.codigo} - {cuenta.nombre}</option>
              ))}
            </select>
          </label>
          <label className="text-sm md:col-span-2 xl:col-span-4">
            Descripcion
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.descripcion} onChange={(event) => setForm((prev) => ({ ...prev, descripcion: event.target.value }))} />
          </label>
          <label className="inline-flex items-center gap-2 self-end text-sm">
            <input type="checkbox" checked={form.acepta_movimientos} onChange={(event) => setForm((prev) => ({ ...prev, acepta_movimientos: event.target.checked }))} />
            Acepta movimientos
          </label>
          <label className="inline-flex items-center gap-2 self-end text-sm">
            <input type="checkbox" checked={form.activa} onChange={(event) => setForm((prev) => ({ ...prev, activa: event.target.checked }))} />
            Activa
          </label>
          <div className="flex items-end">
            <Button type="submit" disabled={saving}>{saving ? 'Guardando...' : 'Agregar cuenta'}</Button>
          </div>
        </form>
      ) : null}

      <div className="rounded-xl border border-border bg-card p-4">
        <div className="mb-3">
          <h3 className="text-lg font-semibold">Cuentas registradas</h3>
          <p className="text-sm text-muted-foreground">Vista clara para revisar codificacion, tipo y estado operativo.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Codigo</th>
                <th className="px-3 py-2 text-left font-medium">Nombre</th>
                <th className="px-3 py-2 text-left font-medium">Tipo</th>
                <th className="px-3 py-2 text-left font-medium">Padre</th>
                <th className="px-3 py-2 text-left font-medium">Imputable</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>Cargando cuentas...</td></tr>
              ) : cuentas.length === 0 ? (
                <tr><td className="px-3 py-3 text-muted-foreground" colSpan={6}>Aun no hay cuentas contables creadas.</td></tr>
              ) : (
                cuentas.map((cuenta) => (
                  <tr key={cuenta.id} className="border-t border-border">
                    <td className="px-3 py-2 font-medium">{cuenta.codigo}</td>
                    <td className="px-3 py-2">{cuenta.nombre}</td>
                    <td className="px-3 py-2">{cuenta.tipo}</td>
                    <td className="px-3 py-2">{cuenta.padre || '-'}</td>
                    <td className="px-3 py-2">{cuenta.acepta_movimientos ? 'Si' : 'No'}</td>
                    <td className="px-3 py-2">{cuenta.activa ? 'Activa' : 'Inactiva'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default ContabilidadPlanPage
