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

function InventarioBodegasPage() {
  const canManage = usePermission('INVENTARIO.CREAR')
  const [bodegas, setBodegas] = useState([])
  const [form, setForm] = useState({ nombre: '', activa: true })

  const loadBodegas = async () => {
    try {
      const { data } = await api.get('/bodegas/', { suppressGlobalErrorToast: true })
      setBodegas(normalizeListResponse(data))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las bodegas.' }))
    }
  }

  useEffect(() => {
    const id = setTimeout(() => { void loadBodegas() }, 0)
    return () => clearTimeout(id)
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    try {
      await api.post('/bodegas/', form, { suppressGlobalErrorToast: true })
      toast.success('Bodega creada.')
      setForm({ nombre: '', activa: true })
      await loadBodegas()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la bodega.' }))
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Bodegas</h2>
        <p className="text-sm text-muted-foreground">Mantenimiento operativo de ubicaciones físicas de inventario.</p>
      </div>

      {canManage ? (
        <form className="flex flex-col gap-3 rounded-md border border-border bg-card p-4 md:flex-row md:items-end" onSubmit={handleSubmit}>
          <label className="text-sm md:min-w-80">
            Nombre
            <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={form.nombre} onChange={(event) => setForm((prev) => ({ ...prev, nombre: event.target.value }))} required />
          </label>
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.activa} onChange={(event) => setForm((prev) => ({ ...prev, activa: event.target.checked }))} />
            Activa
          </label>
          <Button type="submit">Agregar bodega</Button>
        </form>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Nombre</th>
              <th className="px-3 py-2 text-left font-medium">Activa</th>
            </tr>
          </thead>
          <tbody>
            {bodegas.length === 0 ? (
              <tr><td className="px-3 py-3 text-muted-foreground" colSpan={2}>No hay bodegas registradas.</td></tr>
            ) : (
              bodegas.map((bodega) => (
                <tr key={bodega.id} className="border-t border-border">
                  <td className="px-3 py-2">{bodega.nombre}</td>
                  <td className="px-3 py-2">{bodega.activa ? 'Sí' : 'No'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default InventarioBodegasPage
