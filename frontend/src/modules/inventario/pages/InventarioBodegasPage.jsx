import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
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

function normalizeDraftText(value) {
  return String(value || '').toUpperCase()
}

function normalizePayloadText(value) {
  return String(value || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toUpperCase()
}

function getDeleteActionLabel(bodega) {
  if (bodega?.tiene_uso_historico) {
    return 'Inactivar'
  }
  return 'Eliminar'
}

function canExecuteDeleteAction(bodega) {
  if (!bodega) {
    return false
  }
  if (!bodega.tiene_uso_historico) {
    return true
  }
  return Boolean(bodega.activa)
}

function getDeleteDialogCopy(bodega) {
  if (!bodega) {
    return { title: 'Procesar baja de bodega', description: '' }
  }
  if (bodega.tiene_uso_historico) {
    return {
      title: 'Inactivar bodega',
      description: `La bodega "${bodega.nombre}" tiene uso historico y se inactivara para preservar la trazabilidad.`,
    }
  }
  return {
    title: 'Eliminar bodega',
    description: `La bodega "${bodega.nombre}" no tiene historial y se eliminara definitivamente.`,
  }
}

function InventarioBodegasPage() {
  const permissions = usePermissions(['INVENTARIO.CREAR', 'INVENTARIO.EDITAR', 'INVENTARIO.BORRAR'])
  const [bodegas, setBodegas] = useState([])
  const [status, setStatus] = useState('idle')
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [search, setSearch] = useState('')
  const [estadoFiltro, setEstadoFiltro] = useState('TODAS')
  const [pendingDelete, setPendingDelete] = useState(null)
  const [form, setForm] = useState({ id: null, nombre: '', activa: true })

  const loadBodegas = async () => {
    setStatus('loading')
    try {
      const { data } = await api.get('/bodegas/', { suppressGlobalErrorToast: true })
      setBodegas(normalizeListResponse(data))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las bodegas.' }))
    }
  }

  useEffect(() => {
    void loadBodegas()
  }, [])

  const resetForm = () => {
    setForm({ id: null, nombre: '', activa: true })
  }

  const startEdit = (bodega) => {
    setForm({
      id: bodega.id,
      nombre: bodega.nombre || '',
      activa: Boolean(bodega.activa),
    })
  }

  const filteredBodegas = useMemo(() => {
    const query = String(search || '').trim().toUpperCase()
    return bodegas.filter((bodega) => {
      const matchesQuery = !query || String(bodega.nombre || '').toUpperCase().includes(query)
      const matchesEstado =
        estadoFiltro === 'TODAS' ||
        (estadoFiltro === 'ACTIVAS' && bodega.activa) ||
        (estadoFiltro === 'INACTIVAS' && !bodega.activa)
      return matchesQuery && matchesEstado
    })
  }, [bodegas, search, estadoFiltro])

  const summary = useMemo(() => {
    return bodegas.reduce(
      (acc, bodega) => {
        acc.total += 1
        if (bodega.activa) {
          acc.activas += 1
        } else {
          acc.inactivas += 1
        }
        return acc
      },
      { total: 0, activas: 0, inactivas: 0 },
    )
  }, [bodegas])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!(form.id ? permissions['INVENTARIO.EDITAR'] : permissions['INVENTARIO.CREAR'])) {
      toast.error('No tiene permiso para guardar bodegas.')
      return
    }

    const payload = {
      nombre: normalizePayloadText(form.nombre),
      activa: Boolean(form.activa),
    }

    if (!payload.nombre) {
      toast.error('El nombre de la bodega es obligatorio.')
      return
    }

    setSaving(true)
    try {
      if (form.id) {
        await api.patch(`/bodegas/${form.id}/`, payload, { suppressGlobalErrorToast: true })
        toast.success('Bodega actualizada.')
      } else {
        await api.post('/bodegas/', payload, { suppressGlobalErrorToast: true })
        toast.success('Bodega creada.')
      }
      resetForm()
      await loadBodegas()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la bodega.' }))
    } finally {
      setSaving(false)
    }
  }

  const requestDelete = (bodega) => {
    if (!permissions['INVENTARIO.BORRAR']) {
      toast.error('No tiene permiso para eliminar bodegas.')
      return
    }
    setPendingDelete(bodega)
  }

  const handleDelete = async () => {
    if (!pendingDelete) {
      return
    }

    setDeletingId(pendingDelete.id)
    try {
      const response = await api.delete(`/bodegas/${pendingDelete.id}/`, { suppressGlobalErrorToast: true })
      if (response.status === 200 && response.data?.deleted === false) {
        toast.success('La bodega se inactivo porque ya tiene uso historico.')
      } else {
        toast.success('Bodega eliminada.')
      }
      if (form.id === pendingDelete.id) {
        resetForm()
      }
      setPendingDelete(null)
      await loadBodegas()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar la bodega.' }))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Bodegas</h2>
        <p className="text-sm text-muted-foreground">
          Maestro de ubicaciones fisicas de inventario. Las bodegas con uso historico se inactivan en vez de borrarse.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div className="rounded-md border border-border bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Total</p>
          <p className="mt-1 text-2xl font-semibold">{summary.total}</p>
        </div>
        <div className="rounded-md border border-border bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Activas</p>
          <p className="mt-1 text-2xl font-semibold">{summary.activas}</p>
        </div>
        <div className="rounded-md border border-border bg-card px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Inactivas</p>
          <p className="mt-1 text-2xl font-semibold">{summary.inactivas}</p>
        </div>
        <label className="rounded-md border border-border bg-card px-4 py-3 text-sm">
          Buscar bodega
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por nombre"
          />
        </label>
        <label className="rounded-md border border-border bg-card px-4 py-3 text-sm">
          Estado
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={estadoFiltro}
            onChange={(event) => setEstadoFiltro(event.target.value)}
          >
            <option value="TODAS">Todas</option>
            <option value="ACTIVAS">Activas</option>
            <option value="INACTIVAS">Inactivas</option>
          </select>
        </label>
      </div>

      <form
        className="grid grid-cols-1 gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4"
        onSubmit={handleSubmit}
      >
        <label className="text-sm md:col-span-2">
          Nombre
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.nombre}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, nombre: normalizeDraftText(event.target.value) }))
            }
            disabled={saving}
            placeholder="CASA MATRIZ"
          />
        </label>

        <label className="flex items-end gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.activa}
            onChange={(event) => setForm((prev) => ({ ...prev, activa: event.target.checked }))}
            disabled={saving}
          />
          Activa
        </label>

        <div className="flex items-end gap-2">
          {(form.id ? permissions['INVENTARIO.EDITAR'] : permissions['INVENTARIO.CREAR']) ? (
            <Button type="submit" size="sm" disabled={saving}>
              {saving ? 'Guardando...' : form.id ? 'Actualizar bodega' : 'Crear bodega'}
            </Button>
          ) : null}
          {form.id ? (
            <Button type="button" size="sm" variant="outline" onClick={resetForm} disabled={saving}>
              Cancelar
            </Button>
          ) : null}
        </div>
      </form>

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Nombre</th>
              <th className="px-3 py-2 text-left font-medium">Estado</th>
              <th className="px-3 py-2 text-right font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {bodegas.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={3}>
                  {status === 'loading' ? 'Cargando bodegas...' : 'No hay bodegas registradas.'}
                </td>
              </tr>
            ) : filteredBodegas.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={3}>
                  No se encontraron bodegas para la busqueda actual.
                </td>
              </tr>
            ) : (
              filteredBodegas.map((bodega) => (
                <tr key={bodega.id} className="border-t border-border">
                  <td className="px-3 py-2">{bodega.nombre}</td>
                  <td className="px-3 py-2">{bodega.activa ? 'Activa' : 'Inactiva'}</td>
                  <td className="px-3 py-2">
                    <div className="flex justify-end gap-2">
                      {permissions['INVENTARIO.EDITAR'] ? (
                        <Button type="button" size="sm" variant="outline" onClick={() => startEdit(bodega)}>
                          Editar
                        </Button>
                      ) : null}
                      {permissions['INVENTARIO.BORRAR'] ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="border-destructive/40 text-destructive hover:bg-destructive/10"
                          disabled={deletingId === bodega.id || !canExecuteDeleteAction(bodega)}
                          onClick={() => requestDelete(bodega)}
                        >
                          {deletingId === bodega.id ? 'Procesando...' : getDeleteActionLabel(bodega)}
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title={getDeleteDialogCopy(pendingDelete).title}
        description={getDeleteDialogCopy(pendingDelete).description}
        confirmLabel="Confirmar"
        loading={deletingId === pendingDelete?.id}
        onCancel={() => setPendingDelete(null)}
        onConfirm={handleDelete}
      />
    </section>
  )
}

export default InventarioBodegasPage
