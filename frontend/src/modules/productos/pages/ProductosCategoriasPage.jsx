import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function ProductosCategoriasPage() {
  const permissions = usePermissions(['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'])
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('idle')
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [form, setForm] = useState({
    id: null,
    nombre: '',
    descripcion: '',
    activa: true,
  })

  const loadData = async () => {
    setStatus('loading')
    try {
      const { data } = await api.get('/categorias/', { suppressGlobalErrorToast: true })
      setRows(normalizeListResponse(data))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las categorias.' }))
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const resetForm = () => {
    setForm({ id: null, nombre: '', descripcion: '', activa: true })
  }

  const startEdit = (row) => {
    setForm({
      id: row.id,
      nombre: row.nombre || '',
      descripcion: row.descripcion || '',
      activa: Boolean(row.activa),
    })
  }

  const submitForm = async (event) => {
    event.preventDefault()
    if (!(form.id ? permissions['PRODUCTOS.EDITAR'] : permissions['PRODUCTOS.CREAR'])) {
      toast.error('No tiene permiso para guardar categorias.')
      return
    }

    const payload = {
      nombre: String(form.nombre || '').trim(),
      descripcion: String(form.descripcion || '').trim(),
      activa: Boolean(form.activa),
    }

    if (!payload.nombre) {
      toast.error('El nombre de la categoria es obligatorio.')
      return
    }

    setSaving(true)
    try {
      if (form.id) {
        await api.patch(`/categorias/${form.id}/`, payload, { suppressGlobalErrorToast: true })
        toast.success('Categoria actualizada.')
      } else {
        await api.post('/categorias/', payload, { suppressGlobalErrorToast: true })
        toast.success('Categoria creada.')
      }

      resetForm()
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la categoria.' }))
    } finally {
      setSaving(false)
    }
  }

  const removeRow = async (id) => {
    if (!permissions['PRODUCTOS.BORRAR']) {
      toast.error('No tiene permiso para eliminar categorias.')
      return
    }
    setDeletingId(id)
    try {
      await api.delete(`/categorias/${id}/`, { suppressGlobalErrorToast: true })
      toast.success('Categoria eliminada.')
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar la categoria.' }))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Categorias de productos</h2>
      </div>

      <form className="grid grid-cols-1 gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4" onSubmit={submitForm}>
        <label className="text-sm md:col-span-1">
          Nombre
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.nombre}
            onChange={(event) => setForm((prev) => ({ ...prev, nombre: event.target.value }))}
          />
        </label>
        <label className="text-sm md:col-span-2">
          Descripcion
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.descripcion}
            onChange={(event) => setForm((prev) => ({ ...prev, descripcion: event.target.value }))}
          />
        </label>
        <label className="flex items-end gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.activa}
            onChange={(event) => setForm((prev) => ({ ...prev, activa: event.target.checked }))}
          />
          Activa
        </label>

        <div className="flex items-center gap-2 md:col-span-4">
          <Button type="submit" size="sm" disabled={saving}>
            {saving ? 'Guardando...' : form.id ? 'Actualizar categoria' : 'Crear categoria'}
          </Button>
          {form.id ? (
            <Button type="button" variant="outline" size="sm" onClick={resetForm}>
              Cancelar edicion
            </Button>
          ) : null}
        </div>
      </form>

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Nombre</th>
              <th className="px-3 py-2 text-left font-medium">Descripcion</th>
              <th className="px-3 py-2 text-left font-medium">Estado</th>
              <th className="px-3 py-2 text-right font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={4}>
                  {status === 'loading' ? 'Cargando categorias...' : 'No hay categorias cargadas.'}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-3 py-2">{row.nombre || '-'}</td>
                  <td className="px-3 py-2">{row.descripcion || '-'}</td>
                  <td className="px-3 py-2">{row.activa ? 'Activa' : 'Inactiva'}</td>
                  <td className="px-3 py-2">
                    <div className="flex justify-end gap-2">
                      {permissions['PRODUCTOS.EDITAR'] ? (
                        <Button type="button" size="sm" variant="outline" onClick={() => startEdit(row)}>
                          Editar
                        </Button>
                      ) : null}
                      {permissions['PRODUCTOS.BORRAR'] ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="border-destructive/40 text-destructive hover:bg-destructive/10"
                          disabled={deletingId === row.id}
                          onClick={() => removeRow(row.id)}
                        >
                          {deletingId === row.id ? 'Eliminando...' : 'Eliminar'}
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
    </div>
  )
}

export default ProductosCategoriasPage
