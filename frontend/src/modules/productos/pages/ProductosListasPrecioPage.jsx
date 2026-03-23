import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { normalizeUpperInput } from '@/lib/textFormat'
import { cn } from '@/lib/utils'
import { productosApi } from '@/modules/productos/store/api'
import { usePermissions } from '@/modules/shared/auth/usePermission'

const PRIORIDAD_OPTIONS = [
  {
    value: '10',
    label: 'Urgente',
    description: 'Se aplica antes que otras listas equivalentes cuando coincide vigencia y alcance.',
  },
  {
    value: '50',
    label: 'Alta',
    description: 'Prioridad elevada para clientes o campanas preferentes.',
  },
  {
    value: '100',
    label: 'Normal',
    description: 'Nivel recomendado para la mayoria de las listas base.',
  },
  {
    value: '200',
    label: 'Respaldo',
    description: 'Sirve como lista secundaria o fallback comercial.',
  },
]

function emptyListaForm() {
  return {
    id: null,
    nombre: '',
    moneda: '',
    cliente: '',
    fecha_desde: '',
    fecha_hasta: '',
    prioridad: '100',
    activa: true,
  }
}

function getPriorityOption(value) {
  return PRIORIDAD_OPTIONS.find((option) => option.value === String(value)) || null
}

function getPriorityOptionsForValue(value) {
  const normalizedValue = String(value ?? '')
  const matched = getPriorityOption(normalizedValue)
  if (matched) {
    return PRIORIDAD_OPTIONS
  }
  if (!normalizedValue) {
    return PRIORIDAD_OPTIONS
  }
  return [
    ...PRIORIDAD_OPTIONS,
    {
      value: normalizedValue,
      label: 'Personalizada',
      description: 'Valor heredado de una configuracion anterior.',
    },
  ]
}

function formatPriorityDisplay(lista) {
  const value = String(lista?.prioridad ?? '')
  const matched = getPriorityOption(value)
  if (matched) {
    return matched.label
  }
  if (!value) {
    return '-'
  }
  return 'Personalizada'
}

function ProductosListasPrecioPage() {
  const permissions = usePermissions(['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'])
  const [listas, setListas] = useState([])
  const [monedas, setMonedas] = useState([])
  const [clientes, setClientes] = useState([])
  const [status, setStatus] = useState('idle')
  const [savingLista, setSavingLista] = useState(false)
  const [deletingTarget, setDeletingTarget] = useState(null)
  const [formLista, setFormLista] = useState(emptyListaForm)

  const loadBaseData = useCallback(async () => {
    setStatus('loading')
    try {
      const [
        listasData,
        monedasData,
        clientesData,
      ] = await Promise.all([
        productosApi.getList(productosApi.endpoints.listasPrecio),
        productosApi.getList(productosApi.endpoints.monedas),
        productosApi.getList(productosApi.endpoints.clientes),
      ])
      setListas(listasData)
      setMonedas(monedasData)
      setClientes(clientesData)
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las listas de precio.' }))
    }
  }, [])

  useEffect(() => {
    const id = setTimeout(() => { void loadBaseData() }, 0)
    return () => clearTimeout(id)
  }, [loadBaseData])

  const clienteLabelById = useMemo(() => {
    const map = new Map()
    clientes.forEach((cliente) => {
      map.set(String(cliente.id), cliente.contacto_nombre || cliente.nombre || String(cliente.id))
    })
    return map
  }, [clientes])

  const monedaLabelById = useMemo(() => {
    const map = new Map()
    monedas.forEach((moneda) => {
      map.set(String(moneda.id), moneda.codigo || moneda.nombre || String(moneda.id))
    })
    return map
  }, [monedas])

  const prioridadOptions = useMemo(() => getPriorityOptionsForValue(formLista.prioridad), [formLista.prioridad])
  const prioridadSeleccionada = useMemo(() => {
    return prioridadOptions.find((option) => option.value === String(formLista.prioridad)) || null
  }, [formLista.prioridad, prioridadOptions])

  const resetListaForm = () => setFormLista(emptyListaForm())

  const startEditLista = (lista) => {
    setFormLista({
      id: lista.id,
      nombre: lista.nombre || '',
      moneda: String(lista.moneda || ''),
      cliente: lista.cliente ? String(lista.cliente) : '',
      fecha_desde: lista.fecha_desde || '',
      fecha_hasta: lista.fecha_hasta || '',
      prioridad: String(lista.prioridad ?? '100'),
      activa: Boolean(lista.activa),
    })
  }

  const submitLista = async (event) => {
    event.preventDefault()
    if (!(formLista.id ? permissions['PRODUCTOS.EDITAR'] : permissions['PRODUCTOS.CREAR'])) {
      toast.error('No tiene permiso para guardar listas de precio.')
      return
    }

    const prioridad = Number(String(formLista.prioridad || '100').trim())
    const payload = {
      nombre: String(formLista.nombre || '').trim(),
      moneda: formLista.moneda || null,
      cliente: formLista.cliente || null,
      fecha_desde: formLista.fecha_desde || null,
      fecha_hasta: formLista.fecha_hasta || null,
      prioridad: Number.isFinite(prioridad) ? prioridad : null,
      activa: Boolean(formLista.activa),
    }

    if (!payload.nombre || !payload.moneda || !payload.fecha_desde) {
      toast.error('Nombre, moneda y vigencia desde son obligatorios.')
      return
    }
    if (payload.prioridad === null || payload.prioridad < 0) {
      toast.error('La prioridad debe ser un numero positivo.')
      return
    }

    setSavingLista(true)
    try {
      if (formLista.id) {
        await productosApi.updateOne(productosApi.endpoints.listasPrecio, formLista.id, payload)
        toast.success('Lista de precio actualizada.')
      } else {
        await productosApi.createOne(productosApi.endpoints.listasPrecio, payload)
        toast.success('Lista de precio creada.')
      }
      resetListaForm()
      await loadBaseData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la lista.' }))
    } finally {
      setSavingLista(false)
    }
  }

  const confirmDelete = async () => {
    if (!deletingTarget) {
      return
    }
    if (!permissions['PRODUCTOS.BORRAR']) {
      toast.error('No tiene permiso para eliminar listas de precio.')
      return
    }

    try {
      await productosApi.removeOne(productosApi.endpoints.listasPrecio, deletingTarget.id)
      toast.success('Lista de precio procesada correctamente.')
      if (String(formLista.id) === String(deletingTarget.id)) {
        resetListaForm()
      }
      setDeletingTarget(null)
      await loadBaseData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el registro.' }))
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Listas de precio</h2>
        <p className="text-sm text-muted-foreground">Administre cabeceras comerciales por cliente, vigencia y prioridad. Los precios por producto se gestionan dentro de cada lista.</p>
      </div>

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4" onSubmit={submitLista}>
        <label className="text-sm md:col-span-2">
          Nombre lista
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={formLista.nombre}
            onChange={(event) => setFormLista((prev) => ({ ...prev, nombre: normalizeUpperInput(event.target.value) }))}
            required
          />
        </label>
        <label className="text-sm">
          Moneda
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.moneda} onChange={(event) => setFormLista((prev) => ({ ...prev, moneda: event.target.value }))} required>
            <option value="">Seleccione</option>
            {monedas.map((moneda) => <option key={moneda.id} value={moneda.id}>{moneda.codigo}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Cliente
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.cliente} onChange={(event) => setFormLista((prev) => ({ ...prev, cliente: event.target.value }))}>
            <option value="">Lista general</option>
            {clientes.map((cliente) => <option key={cliente.id} value={cliente.id}>{cliente.contacto_nombre || cliente.id}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Vigencia desde
          <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.fecha_desde} onChange={(event) => setFormLista((prev) => ({ ...prev, fecha_desde: event.target.value }))} required />
        </label>
        <label className="text-sm">
          Vigencia hasta
          <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.fecha_hasta} onChange={(event) => setFormLista((prev) => ({ ...prev, fecha_hasta: event.target.value }))} />
        </label>
        <label className="text-sm" htmlFor="lista-prioridad">
          Nivel comercial
        </label>
        <div className="text-sm">
          <select id="lista-prioridad" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.prioridad} onChange={(event) => setFormLista((prev) => ({ ...prev, prioridad: event.target.value }))}>
            {prioridadOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-muted-foreground">
            {prioridadSeleccionada?.description || 'La prioridad comercial ordena que lista se aplica primero cuando hay conflicto.'}
          </span>
        </div>
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={formLista.activa} onChange={(event) => setFormLista((prev) => ({ ...prev, activa: event.target.checked }))} />
          Activa
        </label>
        <div className="flex gap-2 md:col-span-4">
          <Button type="submit" disabled={savingLista}>{savingLista ? 'Guardando...' : (formLista.id ? 'Actualizar lista' : 'Crear lista')}</Button>
          {formLista.id ? <Button type="button" variant="outline" onClick={resetListaForm}>Cancelar</Button> : null}
        </div>
      </form>

      <div className="rounded-md border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-base font-semibold">Listas registradas</h3>
          <p className="text-sm text-muted-foreground">Ingrese a una lista para gestionar sus precios por producto e importaciones masivas.</p>
        </div>

        {status === 'loading' ? (
          <p className="px-4 py-4 text-sm text-muted-foreground">Cargando listas...</p>
        ) : status === 'failed' ? (
          <p className="px-4 py-4 text-sm text-destructive">No se pudieron cargar las listas de precio.</p>
        ) : listas.length === 0 ? (
          <p className="px-4 py-4 text-sm text-muted-foreground">No hay listas de precio registradas.</p>
        ) : (
          <div className="divide-y divide-border">
            {listas.map((lista) => (
              <div key={lista.id} className="flex flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{lista.nombre}</p>
                  <p className="text-xs text-muted-foreground">
                    {clienteLabelById.get(String(lista.cliente || '')) || 'Lista general'} | {monedaLabelById.get(String(lista.moneda || '')) || '-'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {lista.fecha_desde || '-'} {lista.fecha_hasta ? `a ${lista.fecha_hasta}` : 'sin termino'} | {formatPriorityDisplay(lista)} | {lista.activa ? 'Activa' : 'Inactiva'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    to={`/productos/listas-precio/${lista.id}`}
                    className={cn(buttonVariants({ variant: 'outline', size: 'sm' }))}
                  >
                    Gestionar precios
                  </Link>
                  {permissions['PRODUCTOS.EDITAR'] ? (
                    <Button type="button" size="sm" variant="outline" onClick={() => startEditLista(lista)}>
                      Editar cabecera
                    </Button>
                  ) : null}
                  {permissions['PRODUCTOS.BORRAR'] ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="border-destructive/40 text-destructive hover:bg-destructive/10"
                      onClick={() => setDeletingTarget({ id: lista.id, label: lista.nombre })}
                    >
                      Eliminar
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(deletingTarget)}
        title="Eliminar lista de precio"
        description={
          deletingTarget
            ? `Se procesara la lista "${deletingTarget.label}". Si tiene historial comercial podria quedar desactivada en lugar de eliminarse.`
            : ''
        }
        confirmLabel="Confirmar"
        onCancel={() => setDeletingTarget(null)}
        onConfirm={confirmDelete}
      />
    </section>
  )
}

export default ProductosListasPrecioPage
