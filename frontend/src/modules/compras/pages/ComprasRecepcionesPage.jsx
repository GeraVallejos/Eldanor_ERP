import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function todayDate() {
  return new Date().toISOString().slice(0, 10)
}

function ComprasRecepcionesPage() {
  const [status, setStatus] = useState('idle')
  const [recepciones, setRecepciones] = useState([])
  const [ordenes, setOrdenes] = useState([])
  const [ordenItems, setOrdenItems] = useState([])
  const [productos, setProductos] = useState([])
  const [confirmingId, setConfirmingId] = useState(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({
    orden_compra: '',
    fecha: todayDate(),
    orden_item: '',
    producto: '',
    cantidad: '1',
  })

  const loadData = async () => {
    setStatus('loading')
    try {
      const [recepcionesRes, ordenesRes, ordenItemsRes, productosRes] = await Promise.all([
        api.get('/recepciones-compra/', { suppressGlobalErrorToast: true }),
        api.get('/ordenes-compra/', { suppressGlobalErrorToast: true }),
        api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true }),
        api.get('/productos/', { suppressGlobalErrorToast: true }),
      ])

      setRecepciones(normalizeListResponse(recepcionesRes.data))
      setOrdenes(normalizeListResponse(ordenesRes.data))
      setOrdenItems(normalizeListResponse(ordenItemsRes.data))
      setProductos(normalizeListResponse(productosRes.data))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las recepciones.' }))
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  const ordenById = useMemo(() => {
    const map = new Map()
    ordenes.forEach((orden) => map.set(String(orden.id), orden))
    return map
  }, [ordenes])

  const selectedOrdenItems = useMemo(() => {
    if (!form.orden_compra) {
      return []
    }

    return ordenItems.filter((item) => String(item.orden_compra) === String(form.orden_compra))
  }, [form.orden_compra, ordenItems])

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))

    if (key === 'orden_compra') {
      setForm((prev) => ({ ...prev, orden_compra: value, orden_item: '', producto: '' }))
    }

    if (key === 'orden_item') {
      const item = ordenItems.find((row) => String(row.id) === String(value))
      setForm((prev) => ({ ...prev, orden_item: value, producto: item?.producto ? String(item.producto) : '' }))
    }
  }

  const createRecepcion = async (event) => {
    event.preventDefault()
    if (!form.orden_compra || !form.orden_item || !form.producto) {
      toast.error('Completa orden, item y producto para crear la recepcion.')
      return
    }

    setCreating(true)
    try {
      const { data: recepcion } = await api.post(
        '/recepciones-compra/',
        {
          orden_compra: form.orden_compra,
          fecha: form.fecha,
          estado: 'BORRADOR',
        },
        { suppressGlobalErrorToast: true },
      )

      await api.post(
        '/recepciones-compra-items/',
        {
          recepcion: recepcion.id,
          orden_item: form.orden_item,
          producto: form.producto,
          cantidad: Number(form.cantidad),
        },
        { suppressGlobalErrorToast: true },
      )

      toast.success('Recepcion creada en borrador.')
      setForm((prev) => ({ ...prev, orden_item: '', producto: '', cantidad: '1' }))
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la recepcion.' }))
    } finally {
      setCreating(false)
    }
  }

  const confirmRecepcion = async (recepcion) => {
    setConfirmingId(recepcion.id)
    try {
      await api.post(`/recepciones-compra/${recepcion.id}/confirmar/`, {}, { suppressGlobalErrorToast: true })
      toast.success('Recepcion confirmada e inventario actualizado.')
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo confirmar la recepcion.' }))
    } finally {
      setConfirmingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Recepciones de compra</h2>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadData}>
            Recargar
          </Button>
          <Link to="/compras/ordenes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Ver ordenes
          </Link>
        </div>
      </div>

      <form className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-5" onSubmit={createRecepcion}>
        <label className="text-sm">
          Orden
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.orden_compra}
            onChange={(event) => updateField('orden_compra', event.target.value)}
            required
          >
            <option value="">Selecciona</option>
            {ordenes.map((orden) => (
              <option key={orden.id} value={orden.id}>
                {orden.numero} ({orden.estado})
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          Item orden
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.orden_item}
            onChange={(event) => updateField('orden_item', event.target.value)}
            required
          >
            <option value="">Selecciona</option>
            {selectedOrdenItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.descripcion}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          Producto
          <select
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.producto}
            onChange={(event) => updateField('producto', event.target.value)}
            required
          >
            <option value="">Selecciona</option>
            {productos.map((producto) => (
              <option key={producto.id} value={producto.id}>
                {producto.nombre}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          Cantidad
          <input
            type="number"
            min="0.01"
            step="0.01"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
            value={form.cantidad}
            onChange={(event) => updateField('cantidad', event.target.value)}
            required
          />
        </label>

        <div className="flex items-end">
          <Button type="submit" disabled={creating}>
            {creating ? 'Creando...' : 'Crear recepcion'}
          </Button>
        </div>
      </form>

      {status === 'loading' ? <p className="text-sm text-muted-foreground">Cargando recepciones...</p> : null}

      {status === 'succeeded' ? (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">ID</th>
                <th className="px-3 py-2 text-left font-medium">Orden</th>
                <th className="px-3 py-2 text-left font-medium">Fecha</th>
                <th className="px-3 py-2 text-left font-medium">Estado</th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {recepciones.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={5}>
                    No hay recepciones.
                  </td>
                </tr>
              ) : (
                recepciones.map((recepcion) => {
                  const orden = ordenById.get(String(recepcion.orden_compra))

                  return (
                    <tr key={recepcion.id} className="border-t border-border">
                      <td className="px-3 py-2">{String(recepcion.id).slice(0, 8)}</td>
                      <td className="px-3 py-2">{orden?.numero || '-'}</td>
                      <td className="px-3 py-2">{recepcion.fecha || '-'}</td>
                      <td className="px-3 py-2">{recepcion.estado || '-'}</td>
                      <td className="px-3 py-2 text-right">
                        {recepcion.estado === 'BORRADOR' ? (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={confirmingId === recepcion.id}
                            onClick={() => confirmRecepcion(recepcion)}
                          >
                            {confirmingId === recepcion.id ? 'Confirmando...' : 'Confirmar'}
                          </Button>
                        ) : null}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}

export default ComprasRecepcionesPage
