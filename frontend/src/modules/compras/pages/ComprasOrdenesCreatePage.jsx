import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
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

function createEmptyItem() {
  return {
    producto: '',
    descripcion: '',
    cantidad: '1',
    precio_unitario: '0',
    impuesto: '',
  }
}

function todayDate() {
  return new Date().toISOString().slice(0, 10)
}

function ComprasOrdenesCreatePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { id: ordenId } = useParams()
  const isEditMode = Boolean(ordenId)
  const precargarDe = !isEditMode ? (location.state?.precargarDe ?? null) : null
  const [status, setStatus] = useState('idle')
  const [loadingInitial, setLoadingInitial] = useState(true)
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [productos, setProductos] = useState([])
  const [impuestos, setImpuestos] = useState([])
  const [numeroPreview, setNumeroPreview] = useState('...')
  const [form, setForm] = useState({
    proveedor: '',
    fecha_emision: todayDate(),
    fecha_entrega: '',
    observaciones: '',
  })
  const [items, setItems] = useState([createEmptyItem()])

  const loadInitialData = useCallback(async () => {
    setLoadingInitial(true)
    try {
      const [
        { data: proveedoresData },
        { data: contactosData },
        { data: productosData },
        { data: impuestosData },
      ] = await Promise.all([
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
        api.get('/productos/', { suppressGlobalErrorToast: true }),
        api.get('/impuestos/', { suppressGlobalErrorToast: true }),
      ])

      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setProductos(
        normalizeListResponse(productosData).filter(
          (producto) => String(producto.tipo || '').toUpperCase() === 'PRODUCTO',
        ),
      )
      setImpuestos(normalizeListResponse(impuestosData))

      if (isEditMode) {
        const [{ data: ordenData }, { data: itemsData }] = await Promise.all([
          api.get(`/ordenes-compra/${ordenId}/`, { suppressGlobalErrorToast: true }),
          api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true }),
        ])

        setForm({
          proveedor: String(ordenData.proveedor || ''),
          fecha_emision: ordenData.fecha_emision || todayDate(),
          fecha_entrega: ordenData.fecha_entrega || '',
          observaciones: ordenData.observaciones || '',
        })

        if (ordenData.estado !== 'BORRADOR') {
          toast.error('Solo se pueden editar órdenes en estado borrador. Use la acción corregir para órdenes ya enviadas.')
          navigate('/compras/ordenes', { replace: true })
          return
        }

        setNumeroPreview(String(ordenData.numero || '-'))

        const scopedItems = normalizeListResponse(itemsData).filter(
          (row) => String(row.orden_compra) === String(ordenId),
        )

        setItems(
          scopedItems.length > 0
            ? scopedItems.map((item) => ({
                producto: String(item.producto || ''),
                descripcion: item.descripcion || '',
                cantidad: String(item.cantidad || '1'),
                precio_unitario: String(item.precio_unitario || '0'),
                impuesto: item.impuesto ? String(item.impuesto) : '',
              }))
            : [createEmptyItem()],
        )
      } else {
        const { data: numeroData } = await api.get('/ordenes-compra/siguiente_numero/', {
          suppressGlobalErrorToast: true,
        })
        setNumeroPreview(String(numeroData?.numero || '-'))

        if (precargarDe) {
          setForm({
            proveedor: precargarDe.proveedor,
            fecha_emision: precargarDe.fecha_emision || todayDate(),
            fecha_entrega: precargarDe.fecha_entrega || '',
            observaciones: precargarDe.observaciones || '',
          })
          setItems(precargarDe.items?.length > 0 ? precargarDe.items : [createEmptyItem()])
        }
      }
    } catch (error) {
      setNumeroPreview('-')
      toast.error(
        normalizeApiError(error, {
          fallback: isEditMode
            ? 'No se pudo cargar la orden para editar.'
            : 'No se pudieron cargar los catalogos de compras.',
        }),
      )
    } finally {
      setLoadingInitial(false)
    }
  }, [isEditMode, navigate, ordenId, precargarDe])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadInitialData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [loadInitialData])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => map.set(String(contacto.id), contacto))
    return map
  }, [contactos])

  const proveedorOptions = useMemo(() => {
    return proveedores.map((proveedor) => {
      const contacto = contactoById.get(String(proveedor.contacto))
      return {
        id: String(proveedor.id),
        label: contacto?.nombre || `Proveedor #${proveedor.id}`,
      }
    })
  }, [proveedores, contactoById])

  const impuestoById = useMemo(() => {
    const map = new Map()
    impuestos.forEach((impuesto) => map.set(String(impuesto.id), impuesto))
    return map
  }, [impuestos])

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const updateItemField = (index, key, value) => {
    setItems((prev) => {
      const next = [...prev]
      const row = { ...next[index], [key]: value }

      if (key === 'producto') {
        const selected = productos.find((producto) => String(producto.id) === String(value))
        if (selected) {
          row.descripcion = selected.nombre || ''
          row.precio_unitario = String(Math.round(Number(selected.precio_referencia || 0)))
          row.impuesto = selected.impuesto ? String(selected.impuesto) : ''
        }
      }

      next[index] = row
      return next
    })
  }

  const addItem = () => {
    setItems((prev) => [...prev, createEmptyItem()])
  }

  const removeItem = (index) => {
    if (items.length <= 1) {
      toast.error('Debes agregar al menos un item.')
      return
    }

    setItems((prev) => prev.filter((_, idx) => idx !== index))
  }

  const computeItemTotals = (item) => {
    const cantidad = Number(item.cantidad)
    const precioUnitario = Number(item.precio_unitario)
    const safeCantidad = Number.isFinite(cantidad) && cantidad > 0 ? cantidad : 0
    const safePrecio = Number.isFinite(precioUnitario) && precioUnitario >= 0 ? precioUnitario : 0
    const subtotal = safeCantidad * safePrecio

    const impuesto = item.impuesto ? impuestoById.get(String(item.impuesto)) : null
    const tasa = Number(impuesto?.porcentaje || 0)
    const safeTasa = Number.isFinite(tasa) && tasa >= 0 ? tasa : 0
    const total = subtotal + subtotal * (safeTasa / 100)

    return { subtotal, total }
  }

  const onSubmit = async (event) => {
    event.preventDefault()

    if (!form.proveedor) {
      toast.error('Debes seleccionar un proveedor.')
      return
    }

    const hasInvalidItem = items.some(
      (item) => !item.producto || !String(item.descripcion || '').trim() || Number(item.cantidad) <= 0,
    )
    if (hasInvalidItem) {
      toast.error('Completa correctamente los items de la orden.')
      return
    }

    setStatus('loading')

    try {
      const totals = items.map(computeItemTotals)
      const subtotal = totals.reduce((acc, row) => acc + row.subtotal, 0)
      const total = totals.reduce((acc, row) => acc + row.total, 0)
      const impuestosTotal = total - subtotal

      const payload = {
        proveedor: form.proveedor,
        estado: 'BORRADOR',
        fecha_emision: form.fecha_emision,
        fecha_entrega: form.fecha_entrega || null,
        observaciones: form.observaciones || '',
        subtotal,
        impuestos: impuestosTotal,
        total,
      }

      let targetOrdenId = ordenId
      if (isEditMode) {
        await api.patch(`/ordenes-compra/${ordenId}/`, payload, { suppressGlobalErrorToast: true })

        const { data: existingItemsData } = await api.get('/ordenes-compra-items/', {
          suppressGlobalErrorToast: true,
        })
        const existingItems = normalizeListResponse(existingItemsData).filter(
          (row) => String(row.orden_compra) === String(ordenId),
        )

        await Promise.all(
          existingItems.map((row) =>
            api.delete(`/ordenes-compra-items/${row.id}/`, { suppressGlobalErrorToast: true }),
          ),
        )
      } else {
        const { data: orden } = await api.post('/ordenes-compra/', payload, {
          suppressGlobalErrorToast: true,
        })
        targetOrdenId = orden.id
      }

      await Promise.all(
        items.map((item, index) => {
          const totalsByItem = totals[index]
          return api.post(
            '/ordenes-compra-items/',
            {
              orden_compra: targetOrdenId,
              producto: item.producto,
              descripcion: item.descripcion,
              cantidad: Number(item.cantidad),
              precio_unitario: Number(item.precio_unitario),
              impuesto: item.impuesto || null,
              subtotal: totalsByItem.subtotal,
              total: totalsByItem.total,
            },
            { suppressGlobalErrorToast: true },
          )
        }),
      )

      toast.success(isEditMode ? 'Orden de compra actualizada correctamente.' : 'Orden de compra creada correctamente.')
      navigate('/compras/ordenes')
    } catch (error) {
      toast.error(
        normalizeApiError(error, {
          fallback: isEditMode ? 'No se pudo actualizar la orden de compra.' : 'No se pudo crear la orden de compra.',
        }),
      )
    } finally {
      setStatus('idle')
    }
  }

  if (loadingInitial) {
    return <p className="text-sm text-muted-foreground">Cargando orden...</p>
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">{isEditMode ? 'Editar orden de compra' : precargarDe ? 'Duplicar orden de compra' : 'Nueva orden de compra'}</h2>
          <p className="text-sm text-muted-foreground">Registra la orden y sus items para abastecimiento.</p>
        </div>
        <Link to="/compras/ordenes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
          Volver
        </Link>
      </div>

      <form className="space-y-4 rounded-md border border-border bg-card p-4" onSubmit={onSubmit}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            Proveedor
            <select
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.proveedor}
              onChange={(event) => updateField('proveedor', event.target.value)}
              required
            >
              <option value="">Selecciona proveedor</option>
              {proveedorOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm">
            Numero asignado
            <input
              className="mt-1 w-full rounded-md border border-input bg-muted px-3 py-2 text-muted-foreground"
              value={numeroPreview}
              readOnly
              aria-label="Numero asignado"
            />
          </label>


          <label className="text-sm">
            Fecha emision
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.fecha_emision}
              onChange={(event) => updateField('fecha_emision', event.target.value)}
              required
            />
          </label>

          <label className="text-sm">
            Fecha entrega
            <input
              type="date"
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.fecha_entrega}
              onChange={(event) => updateField('fecha_entrega', event.target.value)}
            />
          </label>

          <label className="text-sm md:col-span-2">
            Observaciones
            <textarea
              rows={3}
              className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
              value={form.observaciones}
              onChange={(event) => updateField('observaciones', event.target.value)}
            />
          </label>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Items</h3>
            <Button type="button" variant="outline" size="sm" onClick={addItem}>
              Agregar item
            </Button>
          </div>

          {items.map((item, index) => (
            <div key={`item-${index}`} className="grid gap-2 rounded-md border border-border p-3 md:grid-cols-6">
              <label className="text-xs md:col-span-2">
                Producto
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                  value={item.producto}
                  onChange={(event) => updateItemField(index, 'producto', event.target.value)}
                  required
                >
                  <option value="">Selecciona producto</option>
                  {productos.map((producto) => (
                    <option key={producto.id} value={producto.id}>
                      {producto.nombre}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-xs md:col-span-2">
                Descripcion
                <input
                  className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                  value={item.descripcion}
                  onChange={(event) => updateItemField(index, 'descripcion', event.target.value)}
                  required
                />
              </label>

              <label className="text-xs">
                Cantidad
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                  value={item.cantidad}
                  onChange={(event) => updateItemField(index, 'cantidad', event.target.value)}
                  required
                />
              </label>

              <label className="text-xs">
                Precio unitario
                <input
                  type="number"
                  min="0"
                  step="1"
                  className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                  value={item.precio_unitario}
                  onChange={(event) => updateItemField(index, 'precio_unitario', event.target.value)}
                  required
                />
              </label>

              <label className="text-xs md:col-span-2">
                Impuesto
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm"
                  value={item.impuesto}
                  onChange={(event) => updateItemField(index, 'impuesto', event.target.value)}
                >
                  <option value="">Sin impuesto</option>
                  {impuestos.map((impuesto) => (
                    <option key={impuesto.id} value={impuesto.id}>
                      {impuesto.nombre}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex items-end md:col-span-4">
                <Button type="button" size="sm" variant="outline" onClick={() => removeItem(index)}>
                  Quitar
                </Button>
              </div>
            </div>
          ))}
        </div>

        <Button type="submit" size="md" disabled={status === 'loading'}>
          {status === 'loading' ? 'Guardando...' : isEditMode ? 'Guardar cambios' : precargarDe ? 'Confirmar duplicado' : 'Crear orden'}
        </Button>
      </form>
    </section>
  )
}

export default ComprasOrdenesCreatePage
