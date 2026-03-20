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

const CLAVE_OPTIONS = [
  { value: 'CAJA', label: 'Caja' },
  { value: 'BANCO', label: 'Banco' },
  { value: 'CLIENTES', label: 'Clientes' },
  { value: 'IVA_CREDITO', label: 'IVA credito fiscal' },
  { value: 'PROVEEDORES', label: 'Proveedores' },
  { value: 'IVA_DEBITO', label: 'IVA debito fiscal' },
  { value: 'CAPITAL', label: 'Capital' },
  { value: 'VENTAS', label: 'Ventas' },
  { value: 'COMPRAS', label: 'Compras y servicios' },
]

const EMPTY_PLAN_FORM = {
  codigo: '',
  nombre: '',
  tipo: 'ACTIVO',
  padre: '',
  acepta_movimientos: true,
  activa: true,
  descripcion: '',
}

const EMPTY_CONFIG_FORM = {
  clave: 'CAJA',
  cuenta: '',
  descripcion: '',
  activa: true,
}

function ContabilidadPlanPage() {
  const canView = usePermission('CONTABILIDAD.VER')
  const canManage = usePermission('CONTABILIDAD.CONTABILIZAR')
  const [loading, setLoading] = useState(true)
  const [savingPlan, setSavingPlan] = useState(false)
  const [savingConfig, setSavingConfig] = useState(false)
  const [seedingPlan, setSeedingPlan] = useState(false)
  const [seedingConfig, setSeedingConfig] = useState(false)
  const [cuentas, setCuentas] = useState([])
  const [configuraciones, setConfiguraciones] = useState([])
  const [planForm, setPlanForm] = useState(EMPTY_PLAN_FORM)
  const [configForm, setConfigForm] = useState(EMPTY_CONFIG_FORM)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [{ data: cuentasData }, { data: configuracionesData }] = await Promise.all([
        api.get('/plan-cuentas/', { suppressGlobalErrorToast: true }),
        api.get('/configuracion-cuentas-contables/', { suppressGlobalErrorToast: true }),
      ])
      setCuentas(normalizeListResponse(cuentasData))
      setConfiguraciones(normalizeListResponse(configuracionesData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la configuracion contable.' }))
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

  const cuentasImputables = useMemo(
    () => cuentas.filter((item) => item.acepta_movimientos && item.activa),
    [cuentas],
  )

  const configuracionesPorClave = useMemo(() => {
    return configuraciones.reduce((acc, item) => {
      acc[item.clave] = item
      return acc
    }, {})
  }, [configuraciones])

  useEffect(() => {
    const actual = configuracionesPorClave[configForm.clave]
    if (actual) {
      setConfigForm({
        clave: actual.clave,
        cuenta: actual.cuenta,
        descripcion: actual.descripcion || '',
        activa: actual.activa,
      })
      return
    }
    setConfigForm((prev) => ({
      ...prev,
      cuenta: '',
      descripcion: '',
      activa: true,
    }))
  }, [configForm.clave, configuracionesPorClave])

  const stats = useMemo(() => ({
    total: cuentas.length,
    activas: cuentas.filter((item) => item.activa).length,
    imputables: cuentas.filter((item) => item.acepta_movimientos).length,
    configuradas: configuraciones.filter((item) => item.activa).length,
  }), [cuentas, configuraciones])

  const handleSeedPlan = async () => {
    setSeedingPlan(true)
    try {
      const { data } = await api.post('/plan-cuentas/seed_base/', {}, { suppressGlobalErrorToast: true })
      toast.success(`Plan base sincronizado. ${data.created || 0} cuentas nuevas.`)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo inicializar el plan base.' }))
    } finally {
      setSeedingPlan(false)
    }
  }

  const handleSeedConfig = async () => {
    setSeedingConfig(true)
    try {
      const { data } = await api.post('/configuracion-cuentas-contables/seed_base/', {}, { suppressGlobalErrorToast: true })
      toast.success(`Configuracion funcional sincronizada. ${data.created || 0} registros nuevos.`)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo inicializar la configuracion funcional.' }))
    } finally {
      setSeedingConfig(false)
    }
  }

  const handlePlanSubmit = async (event) => {
    event.preventDefault()
    setSavingPlan(true)
    try {
      await api.post('/plan-cuentas/', {
        ...planForm,
        padre: planForm.padre || null,
      }, { suppressGlobalErrorToast: true })
      toast.success('Cuenta contable creada.')
      setPlanForm(EMPTY_PLAN_FORM)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la cuenta contable.' }))
    } finally {
      setSavingPlan(false)
    }
  }

  const handleConfigSubmit = async (event) => {
    event.preventDefault()
    setSavingConfig(true)
    try {
      const actual = configuracionesPorClave[configForm.clave]
      const payload = {
        clave: configForm.clave,
        cuenta: configForm.cuenta,
        descripcion: configForm.descripcion,
        activa: configForm.activa,
      }
      if (actual) {
        await api.patch(`/configuracion-cuentas-contables/${actual.id}/`, payload, { suppressGlobalErrorToast: true })
        toast.success('Configuracion contable actualizada.')
      } else {
        await api.post('/configuracion-cuentas-contables/', payload, { suppressGlobalErrorToast: true })
        toast.success('Configuracion contable creada.')
      }
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la configuracion funcional.' }))
    } finally {
      setSavingConfig(false)
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
          <p className="text-sm text-muted-foreground">
            Vista contable para construir el plan, revisar jerarquias y mapear cuentas funcionales usadas por ventas, compras y tesoreria.
          </p>
        </div>
        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={handleSeedConfig} disabled={seedingConfig}>
              {seedingConfig ? 'Sincronizando...' : 'Sincronizar claves base'}
            </Button>
            <Button type="button" onClick={handleSeedPlan} disabled={seedingPlan}>
              {seedingPlan ? 'Inicializando...' : 'Inicializar plan base'}
            </Button>
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Cuentas totales</p>
          <p className="mt-2 text-2xl font-semibold">{stats.total}</p>
          <p className="mt-1 text-xs text-muted-foreground">Incluye agrupadoras y cuentas imputables.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Activas</p>
          <p className="mt-2 text-2xl font-semibold">{stats.activas}</p>
          <p className="mt-1 text-xs text-muted-foreground">Disponibles para imputacion o estructura.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Imputables</p>
          <p className="mt-2 text-2xl font-semibold">{stats.imputables}</p>
          <p className="mt-1 text-xs text-muted-foreground">Aceptan movimientos directos en asientos.</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Claves funcionales activas</p>
          <p className="mt-2 text-2xl font-semibold">{stats.configuradas}</p>
          <p className="mt-1 text-xs text-muted-foreground">Puente entre documentos operativos y contabilidad.</p>
        </div>
      </div>

      {canManage ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(360px,0.9fr)]">
          <form className="space-y-4 rounded-xl border border-border bg-card p-4" onSubmit={handlePlanSubmit}>
            <div>
              <h3 className="text-lg font-semibold">Nueva cuenta contable</h3>
              <p className="text-sm text-muted-foreground">Alta manual para ampliar el plan segun el giro del cliente o ajustes del contador.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
              <label className="text-sm">
                Codigo
                <input
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={planForm.codigo}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, codigo: event.target.value.toUpperCase() }))}
                  required
                />
              </label>
              <label className="text-sm xl:col-span-2">
                Nombre
                <input
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={planForm.nombre}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, nombre: event.target.value }))}
                  required
                />
              </label>
              <label className="text-sm">
                Tipo
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={planForm.tipo}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, tipo: event.target.value }))}
                >
                  <option value="ACTIVO">Activo</option>
                  <option value="PASIVO">Pasivo</option>
                  <option value="PATRIMONIO">Patrimonio</option>
                  <option value="INGRESO">Ingreso</option>
                  <option value="GASTO">Gasto</option>
                </select>
              </label>
              <label className="text-sm xl:col-span-2">
                Cuenta padre
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={planForm.padre}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, padre: event.target.value }))}
                >
                  <option value="">Sin padre</option>
                  {cuentasPadre.map((cuenta) => (
                    <option key={cuenta.id} value={cuenta.id}>
                      {cuenta.codigo} - {cuenta.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm md:col-span-2 xl:col-span-4">
                Descripcion
                <input
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={planForm.descripcion}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, descripcion: event.target.value }))}
                />
              </label>
              <label className="inline-flex items-center gap-2 self-end text-sm">
                <input
                  type="checkbox"
                  checked={planForm.acepta_movimientos}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, acepta_movimientos: event.target.checked }))}
                />
                Acepta movimientos
              </label>
              <label className="inline-flex items-center gap-2 self-end text-sm">
                <input
                  type="checkbox"
                  checked={planForm.activa}
                  onChange={(event) => setPlanForm((prev) => ({ ...prev, activa: event.target.checked }))}
                />
                Activa
              </label>
              <div className="flex items-end">
                <Button type="submit" disabled={savingPlan}>{savingPlan ? 'Guardando...' : 'Agregar cuenta'}</Button>
              </div>
            </div>
          </form>

          <form className="space-y-4 rounded-xl border border-border bg-card p-4" onSubmit={handleConfigSubmit}>
            <div>
              <h3 className="text-lg font-semibold">Claves funcionales</h3>
              <p className="text-sm text-muted-foreground">
                Define que cuenta usa cada flujo automatico. Si la clave ya existe, este formulario la actualiza.
              </p>
            </div>
            <div className="space-y-3">
              <label className="block text-sm">
                Clave funcional
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={configForm.clave}
                  onChange={(event) => setConfigForm((prev) => ({ ...prev, clave: event.target.value }))}
                >
                  {CLAVE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Cuenta imputable
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={configForm.cuenta}
                  onChange={(event) => setConfigForm((prev) => ({ ...prev, cuenta: event.target.value }))}
                  required
                >
                  <option value="">Seleccione una cuenta</option>
                  {cuentasImputables.map((cuenta) => (
                    <option key={cuenta.id} value={cuenta.id}>
                      {cuenta.codigo} - {cuenta.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                Descripcion operativa
                <textarea
                  className="mt-1 min-h-24 w-full rounded-md border border-input bg-background px-3 py-2"
                  value={configForm.descripcion}
                  onChange={(event) => setConfigForm((prev) => ({ ...prev, descripcion: event.target.value }))}
                  placeholder="Ejemplo: cuenta usada para centralizar cobros de clientes"
                />
              </label>
              <label className="inline-flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={configForm.activa}
                  onChange={(event) => setConfigForm((prev) => ({ ...prev, activa: event.target.checked }))}
                />
                Configuracion activa
              </label>
              <div className="flex justify-end">
                <Button type="submit" disabled={savingConfig || !configForm.cuenta}>
                  {savingConfig ? 'Guardando...' : 'Guardar configuracion'}
                </Button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.95fr)]">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Cuentas registradas</h3>
            <p className="text-sm text-muted-foreground">Revisa codificacion, tipo, jerarquia y si la cuenta acepta imputacion directa.</p>
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

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="mb-3">
            <h3 className="text-lg font-semibold">Mapa funcional contable</h3>
            <p className="text-sm text-muted-foreground">Estas claves son las que usa la centralizacion automatica del ERP.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Clave</th>
                  <th className="px-3 py-2 text-left font-medium">Cuenta</th>
                  <th className="px-3 py-2 text-left font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td className="px-3 py-3 text-muted-foreground" colSpan={3}>Cargando configuracion...</td></tr>
                ) : CLAVE_OPTIONS.map((option) => {
                  const item = configuracionesPorClave[option.value]
                  return (
                    <tr key={option.value} className="border-t border-border">
                      <td className="px-3 py-2 font-medium">{option.label}</td>
                      <td className="px-3 py-2">
                        {item ? `${item.cuenta_codigo} - ${item.cuenta_nombre}` : <span className="text-muted-foreground">Sin asignar</span>}
                        {item?.descripcion ? <p className="mt-1 text-xs text-muted-foreground">{item.descripcion}</p> : null}
                      </td>
                      <td className="px-3 py-2">{item ? (item.activa ? 'Activa' : 'Inactiva') : 'Pendiente'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ContabilidadPlanPage
