import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { productosApi } from '@/modules/productos/store/api'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function ProductosImpuestosPage() {
  const permissions = usePermissions(['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'])
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('idle')
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [form, setForm] = useState({
    id: null,
    nombre: '',
    porcentaje: '19',
    activo: true,
  })

  const loadData = async () => {
    setStatus('loading')
    try {
      const data = await productosApi.getList(productosApi.endpoints.impuestos)
      setRows(data)
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los impuestos.' }))
    }
  }

  useEffect(() => {
    void loadData()
  }, [])

  const resetForm = () => {
    setForm({ id: null, nombre: '', porcentaje: '19', activo: true })
  }

  const startEdit = (row) => {
    setForm({
      id: row.id,
      nombre: row.nombre || '',
      porcentaje: String(row.porcentaje ?? '19'),
      activo: Boolean(row.activo),
    })
  }

  const submitForm = async (event) => {
    event.preventDefault()
    if (!(form.id ? permissions['PRODUCTOS.EDITAR'] : permissions['PRODUCTOS.CREAR'])) {
      toast.error('No tiene permiso para guardar impuestos.')
      return
    }

    const porcentaje = Number(String(form.porcentaje || '').replace(',', '.'))
    const payload = {
      nombre: String(form.nombre || '').trim(),
      porcentaje: Number.isFinite(porcentaje) ? porcentaje : null,
      activo: Boolean(form.activo),
    }

    if (!payload.nombre) {
      toast.error('El nombre del impuesto es obligatorio.')
      return
    }
    if (payload.porcentaje === null) {
      toast.error('El porcentaje debe ser numerico.')
      return
    }

    setSaving(true)
    try {
      if (form.id) {
        await productosApi.updateOne(productosApi.endpoints.impuestos, form.id, payload)
        toast.success('Impuesto actualizado.')
      } else {
        await productosApi.createOne(productosApi.endpoints.impuestos, payload)
        toast.success('Impuesto creado.')
      }

      resetForm()
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar el impuesto.' }))
    } finally {
      setSaving(false)
    }
  }

  const removeRow = async (id) => {
    if (!permissions['PRODUCTOS.BORRAR']) {
      toast.error('No tiene permiso para eliminar impuestos.')
      return
    }
    setDeletingId(id)
    try {
      await productosApi.removeOne(productosApi.endpoints.impuestos, id)
      toast.success('Impuesto eliminado.')
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el impuesto.' }))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Impuestos de productos</h2>
      </div>

      <form className="grid grid-cols-1 gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-4" onSubmit={submitForm}>
        <label className="text-sm md:col-span-2">
          Nombre
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.nombre}
            onChange={(event) => setForm((prev) => ({ ...prev, nombre: event.target.value }))}
          />
        </label>
        <label className="text-sm md:col-span-1">
          Porcentaje
          <input
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.porcentaje}
            onChange={(event) => setForm((prev) => ({ ...prev, porcentaje: event.target.value }))}
            placeholder="19"
          />
        </label>
        <label className="flex items-end gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.activo}
            onChange={(event) => setForm((prev) => ({ ...prev, activo: event.target.checked }))}
          />
          Activo
        </label>

        <div className="flex items-center gap-2 md:col-span-4">
          <Button type="submit" size="sm" disabled={saving}>
            {saving ? 'Guardando...' : form.id ? 'Actualizar impuesto' : 'Crear impuesto'}
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
              <th className="px-3 py-2 text-left font-medium">Porcentaje</th>
              <th className="px-3 py-2 text-left font-medium">Estado</th>
              <th className="px-3 py-2 text-right font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={4}>
                  {status === 'loading' ? 'Cargando impuestos...' : 'No hay impuestos cargados.'}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-t border-border">
                  <td className="px-3 py-2">{row.nombre || '-'}</td>
                  <td className="px-3 py-2">{row.porcentaje ?? 0}%</td>
                  <td className="px-3 py-2">{row.activo ? 'Activo' : 'Inactivo'}</td>
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

export default ProductosImpuestosPage
