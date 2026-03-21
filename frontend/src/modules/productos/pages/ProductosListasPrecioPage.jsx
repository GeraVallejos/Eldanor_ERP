import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
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

function ProductosListasPrecioPage() {
  const permissions = usePermissions(['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR'])
  const [listas, setListas] = useState([])
  const [items, setItems] = useState([])
  const [productos, setProductos] = useState([])
  const [monedas, setMonedas] = useState([])
  const [selectedLista, setSelectedLista] = useState('')
  const [formLista, setFormLista] = useState({ nombre: '', moneda: '', fecha_desde: '', activa: true })
  const [formItem, setFormItem] = useState({ producto: '', precio: '' })

  const loadData = async () => {
    try {
      const [
        { data: listasData },
        { data: productosData },
        { data: monedasData },
        { data: itemsData },
      ] = await Promise.all([
        api.get('/listas-precio/', { suppressGlobalErrorToast: true }),
        api.get('/productos/', { suppressGlobalErrorToast: true }),
        api.get('/monedas/', { suppressGlobalErrorToast: true }),
        api.get('/listas-precio-items/', { suppressGlobalErrorToast: true }),
      ])
      setListas(normalizeListResponse(listasData))
      setProductos(normalizeListResponse(productosData))
      setMonedas(normalizeListResponse(monedasData))
      setItems(normalizeListResponse(itemsData))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar las listas de precio.' }))
    }
  }

  useEffect(() => {
    const id = setTimeout(() => { void loadData() }, 0)
    return () => clearTimeout(id)
  }, [])

  const productoLabelById = useMemo(() => {
    const map = new Map()
    productos.forEach((producto) => {
      map.set(String(producto.id), producto.nombre)
    })
    return map
  }, [productos])

  const itemsListaSeleccionada = useMemo(
    () => items.filter((item) => String(item.lista) === String(selectedLista)),
    [items, selectedLista],
  )

  const createLista = async (event) => {
    event.preventDefault()
    if (!permissions['PRODUCTOS.CREAR']) {
      toast.error('No tiene permiso para crear listas de precio.')
      return
    }
    try {
      await api.post('/listas-precio/', formLista, { suppressGlobalErrorToast: true })
      toast.success('Lista de precio creada.')
      setFormLista({ nombre: '', moneda: '', fecha_desde: '', activa: true })
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo crear la lista.' }))
    }
  }

  const createItem = async (event) => {
    event.preventDefault()
    if (!permissions['PRODUCTOS.EDITAR']) {
      toast.error('No tiene permiso para editar listas de precio.')
      return
    }
    try {
      await api.post('/listas-precio-items/', {
        lista: selectedLista,
        producto: formItem.producto,
        precio: formItem.precio,
      }, { suppressGlobalErrorToast: true })
      toast.success('Precio agregado a la lista.')
      setFormItem({ producto: '', precio: '' })
      const { data } = await api.get('/listas-precio-items/', { suppressGlobalErrorToast: true })
      setItems(normalizeListResponse(data))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo agregar el precio.' }))
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Listas de precio</h2>
        <p className="text-sm text-muted-foreground">Gestione listas comerciales y valores especÃ­ficos por producto.</p>
      </div>

      <form className="flex flex-col gap-3 rounded-md border border-border bg-card p-4 md:flex-row md:items-end" onSubmit={createLista}>
        <label className="text-sm md:min-w-80">
          Nombre lista
          <input className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.nombre} onChange={(event) => setFormLista((prev) => ({ ...prev, nombre: event.target.value }))} required />
        </label>
        <label className="text-sm">
          Moneda
          <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.moneda} onChange={(event) => setFormLista((prev) => ({ ...prev, moneda: event.target.value }))} required>
            <option value="">Seleccione</option>
            {monedas.map((moneda) => <option key={moneda.id} value={moneda.id}>{moneda.codigo}</option>)}
          </select>
        </label>
        <label className="text-sm">
          Vigencia desde
          <input type="date" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formLista.fecha_desde} onChange={(event) => setFormLista((prev) => ({ ...prev, fecha_desde: event.target.value }))} required />
        </label>
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" checked={formLista.activa} onChange={(event) => setFormLista((prev) => ({ ...prev, activa: event.target.checked }))} />
          Activa
        </label>
        <Button type="submit">Crear lista</Button>
      </form>

      <div className="grid gap-4 md:grid-cols-[320px_minmax(0,1fr)]">
        <div className="rounded-md border border-border bg-card p-4">
          <label className="text-sm">
            Seleccione lista
            <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={selectedLista} onChange={(event) => setSelectedLista(event.target.value)}>
              <option value="">Seleccione</option>
              {listas.map((lista) => <option key={lista.id} value={lista.id}>{lista.nombre}</option>)}
            </select>
          </label>
        </div>

        <div className="space-y-3 rounded-md border border-border bg-card p-4">
          {selectedLista ? (
            <>
              <form className="grid gap-3 md:grid-cols-3" onSubmit={createItem}>
                <label className="text-sm">
                  Producto
                  <select className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formItem.producto} onChange={(event) => setFormItem((prev) => ({ ...prev, producto: event.target.value }))} required>
                    <option value="">Seleccione</option>
                    {productos.map((producto) => <option key={producto.id} value={producto.id}>{producto.nombre}</option>)}
                  </select>
                </label>
                <label className="text-sm">
                  Precio
                  <input type="number" min="0" step="1" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formItem.precio} onChange={(event) => setFormItem((prev) => ({ ...prev, precio: event.target.value }))} required />
                </label>
                <div className="flex items-end">
                  <Button type="submit">Agregar precio</Button>
                </div>
              </form>

              <div className="overflow-x-auto rounded-md border border-border">
                <table className="min-w-full text-sm">
                  <thead className="bg-muted/40">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Producto</th>
                      <th className="px-3 py-2 text-left font-medium">Precio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {itemsListaSeleccionada.length === 0 ? (
                      <tr><td className="px-3 py-3 text-muted-foreground" colSpan={2}>La lista seleccionada no tiene Ã­tems.</td></tr>
                    ) : (
                      itemsListaSeleccionada.map((item) => (
                        <tr key={item.id} className="border-t border-border">
                          <td className="px-3 py-2">{productoLabelById.get(String(item.producto)) || item.producto}</td>
                          <td className="px-3 py-2">{item.precio}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Seleccione una lista para administrar sus precios.</p>
          )}
        </div>
      </div>
    </section>
  )
}

export default ProductosListasPrecioPage
