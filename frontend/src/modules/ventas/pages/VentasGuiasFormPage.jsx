import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { getChileDateSuffix } from '@/lib/dateTimeFormat'
import { toIntegerString, toQuantityString } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { VENTAS_PERMISSIONS } from '@/modules/ventas/constants'
import { ventasApi } from '@/modules/ventas/store/api'
import { usePermission } from '@/modules/shared/auth/usePermission'

function emptyItem() {
  return { producto: '', descripcion: '', cantidad: '1', precio_unitario: '0', impuesto: '', impuesto_porcentaje: '0' }
}

function VentasGuiasFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [numeroPreview, setNumeroPreview] = useState('...')
  const [estadoActual, setEstadoActual] = useState('')
  const [clientes, setClientes] = useState([])
  const [pedidos, setPedidos] = useState([])
  const [productos, setProductos] = useState([])
  const [impuestos, setImpuestos] = useState([])
  const [form, setForm] = useState({ cliente: '', pedido_venta: '', fecha_despacho: getChileDateSuffix(), observaciones: '' })
  const [items, setItems] = useState([emptyItem()])
  const canCreate = usePermission(VENTAS_PERMISSIONS.crear)
  const canEdit = usePermission(VENTAS_PERMISSIONS.editar)
  const canSubmit = isEdit ? canEdit : canCreate
  const isEditableState = !isEdit || estadoActual === 'BORRADOR'
  const noPermissionMessage = isEdit
    ? 'No tiene permiso para editar guias de despacho.'
    : 'No tiene permiso para crear guias de despacho.'
  const blockedByStateMessage = 'Solo se pueden editar guias en estado BORRADOR.'

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [clientesRows, pedidosRows, productosRows, impuestosRows] = await Promise.all([
        ventasApi.getList('/clientes/'),
        ventasApi.getList(ventasApi.endpoints.pedidos),
        ventasApi.getList('/productos/'),
        ventasApi.getList('/impuestos/'),
      ])
      setClientes(clientesRows)
      setPedidos(pedidosRows)
      setProductos(productosRows)
      setImpuestos(impuestosRows)

      if (isEdit) {
        const guia = await ventasApi.getOne(ventasApi.endpoints.guias, id)
        setEstadoActual(String(guia.estado || ''))
        const itemRows = await ventasApi.getList(ventasApi.endpoints.guiasItems)
        const scoped = itemRows.filter((row) => String(row.guia_despacho) === String(id))
        setNumeroPreview(String(guia.numero || '-'))
        setForm({
          cliente: String(guia.cliente || ''),
          pedido_venta: guia.pedido_venta ? String(guia.pedido_venta) : '',
          fecha_despacho: guia.fecha_despacho || getChileDateSuffix(),
          observaciones: guia.observaciones || '',
        })
        setItems(scoped.length ? scoped.map((row) => ({
          producto: String(row.producto || ''),
          descripcion: row.descripcion || '',
          cantidad: toQuantityString(row.cantidad || 1),
          precio_unitario: toIntegerString(row.precio_unitario || 0),
          impuesto: row.impuesto ? String(row.impuesto) : '',
          impuesto_porcentaje: toIntegerString(row.impuesto_porcentaje || 0),
        })) : [emptyItem()])
      } else {
        setEstadoActual('BORRADOR')
        const next = await ventasApi.getOne(ventasApi.endpoints.guias, 'siguiente_numero')
        setNumeroPreview(String(next?.numero || '-'))
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el formulario de guia.' }))
    } finally {
      setLoading(false)
    }
  }, [id, isEdit])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void load()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [load])

  const clienteOptions = useMemo(
    () => clientes.map((row) => ({ value: String(row.id), label: row.contacto_nombre || row.nombre || String(row.id) })),
    [clientes],
  )

  const productoOptions = useMemo(
    () => productos.map((row) => ({ value: String(row.id), label: row.nombre || String(row.id) })),
    [productos],
  )

  const updateForm = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))
  const updateItem = async (index, key, value) => {
    let productoSeleccionado = null

    setItems((prev) => {
      const next = [...prev]
      const row = { ...next[index], [key]: value }
      if (key === 'producto') {
        const found = productos.find((p) => String(p.id) === String(value))
        if (found) {
          productoSeleccionado = found
          row.descripcion = found.nombre || ''
          row.precio_unitario = toIntegerString(found.precio_referencia || 0)
          row.impuesto = found.impuesto ? String(found.impuesto) : ''
        }
      }
      next[index] = row
      return next
    })

    if (key !== 'producto' || !productoSeleccionado) {
      return
    }

    const precioResuelto = await ventasApi.resolveProductoPrecio(value, {
      cliente_id: form.cliente || undefined,
      fecha: form.fecha_despacho || undefined,
    })

    if (!precioResuelto?.precio) {
      return
    }

    setItems((prev) => {
      const next = [...prev]
      const current = next[index]
      if (!current || String(current.producto) !== String(value)) {
        return prev
      }
      next[index] = {
        ...current,
        precio_unitario: toIntegerString(precioResuelto.precio || productoSeleccionado.precio_referencia || 0),
      }
      return next
    })
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!canSubmit || !isEditableState) {
      toast.error(!canSubmit ? noPermissionMessage : blockedByStateMessage)
      return
    }
    if (!form.cliente) {
      toast.error('Seleccione cliente.')
      return
    }
    if (items.some((row) => !row.producto || Number(row.cantidad) <= 0)) {
      toast.error('Revise items.')
      return
    }

    setSaving(true)
    try {
      const totals = items.map((row) => {
        const subtotal = Number(row.cantidad || 0) * Number(row.precio_unitario || 0)
        const pct = Number(row.impuesto_porcentaje || 0)
        return { subtotal, total: subtotal + subtotal * (pct / 100) }
      })
      const subtotal = totals.reduce((acc, row) => acc + row.subtotal, 0)
      const total = totals.reduce((acc, row) => acc + row.total, 0)
      const payload = {
        cliente: form.cliente,
        pedido_venta: form.pedido_venta || null,
        fecha_despacho: form.fecha_despacho,
        observaciones: form.observaciones || '',
        subtotal,
        impuestos: total - subtotal,
        total,
      }

      let recordId = id
      if (isEdit) {
        await ventasApi.updateOne(ventasApi.endpoints.guias, id, payload)
        const existing = await ventasApi.getList(ventasApi.endpoints.guiasItems)
        const scoped = existing.filter((row) => String(row.guia_despacho) === String(id))
        await Promise.all(scoped.map((row) => ventasApi.removeOne(ventasApi.endpoints.guiasItems, row.id)))
      } else {
        const created = await ventasApi.createOne(ventasApi.endpoints.guias, payload)
        recordId = created.id
      }

      await Promise.all(items.map((row, index) => ventasApi.createOne(ventasApi.endpoints.guiasItems, {
        guia_despacho: recordId,
        pedido_item: null,
        producto: row.producto,
        descripcion: row.descripcion,
        cantidad: Number(row.cantidad),
        precio_unitario: Number(row.precio_unitario),
        impuesto: row.impuesto || null,
        impuesto_porcentaje: Number(row.impuesto_porcentaje || 0),
        subtotal: totals[index].subtotal,
        total: totals[index].total,
      })))

      toast.success(isEdit ? 'Guia actualizada.' : 'Guia creada.')
      navigate('/ventas/guias')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la guia.' }))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-sm text-muted-foreground">Cargando formulario...</p>

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">{isEdit ? 'Editar guia' : 'Nueva guia de despacho'}</h2>
          <p className="text-sm text-muted-foreground">Folio: {numeroPreview}</p>
        </div>
        <Link to="/ventas/guias" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
      </div>

      {!canSubmit || !isEditableState ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {!canSubmit ? noPermissionMessage : blockedByStateMessage}
        </p>
      ) : null}

      <form onSubmit={submit} className="space-y-4">
        <fieldset disabled={!canSubmit || !isEditableState} className="space-y-4">
        <div className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-2">
          <SearchableSelect
            value={form.cliente}
            onChange={(v) => updateForm('cliente', v)}
            options={clienteOptions}
            placeholder="Buscar cliente..."
            ariaLabel="Cliente"
          />
          <select value={form.pedido_venta} onChange={(e) => updateForm('pedido_venta', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="">Pedido (opcional)</option>
            {pedidos.map((row) => <option key={row.id} value={row.id}>{row.numero || row.id}</option>)}
          </select>
          <input type="date" value={form.fecha_despacho} onChange={(e) => updateForm('fecha_despacho', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input value={form.observaciones} onChange={(e) => updateForm('observaciones', e.target.value)} placeholder="Observaciones" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
        </div>

        <div className="space-y-2 rounded-md border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Items</h3>
            <Button type="button" variant="outline" size="sm" onClick={() => setItems((prev) => [...prev, emptyItem()])}>Agregar item</Button>
          </div>
          {items.map((row, index) => (
            <div key={`item-${index}`} className="grid gap-2 rounded-md border border-border p-3 md:grid-cols-5">
              <SearchableSelect
                value={row.producto}
                onChange={(v) => { void updateItem(index, 'producto', v) }}
                options={productoOptions}
                placeholder="Buscar producto..."
                ariaLabel={`Producto item ${index + 1}`}
              />
              <input value={row.descripcion} onChange={(e) => updateItem(index, 'descripcion', e.target.value)} placeholder="Descripcion" className="rounded-md border border-border bg-background px-2 py-2 text-sm" />
              <input value={row.cantidad} onChange={(e) => updateItem(index, 'cantidad', toQuantityString(e.target.value))} placeholder="Cantidad" className="rounded-md border border-border bg-background px-2 py-2 text-sm" />
              <input value={row.precio_unitario} onChange={(e) => updateItem(index, 'precio_unitario', toIntegerString(e.target.value))} placeholder="Precio" className="rounded-md border border-border bg-background px-2 py-2 text-sm" />
              <div className="flex gap-2">
                <select value={row.impuesto} onChange={(e) => updateItem(index, 'impuesto', e.target.value)} className="min-w-0 flex-1 rounded-md border border-border bg-background px-2 py-2 text-sm">
                  <option value="">IVA</option>
                  {impuestos.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
                </select>
                <Button type="button" variant="destructive" size="sm" onClick={() => setItems((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)))}>Quitar</Button>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2">
          <Link to="/ventas/guias" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Cancelar</Link>
          <Button type="submit" disabled={saving || !canSubmit || !isEditableState}>{saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear guia'}</Button>
        </div>
        </fieldset>
      </form>
    </section>
  )
}

export default VentasGuiasFormPage
