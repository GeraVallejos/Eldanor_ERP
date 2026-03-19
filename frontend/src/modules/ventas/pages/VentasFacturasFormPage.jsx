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
  return { producto: '', descripcion: '', cantidad: '1', precio_unitario: '0', descuento: '0', impuesto: '', impuesto_porcentaje: '0' }
}

function VentasFacturasFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [numeroPreview, setNumeroPreview] = useState('...')
  const [clientes, setClientes] = useState([])
  const [pedidos, setPedidos] = useState([])
  const [guias, setGuias] = useState([])
  const [productos, setProductos] = useState([])
  const [impuestos, setImpuestos] = useState([])
  const [form, setForm] = useState({ cliente: '', pedido_venta: '', guia_despacho: '', fecha_emision: getChileDateSuffix(), fecha_vencimiento: getChileDateSuffix(), observaciones: '' })
  const [items, setItems] = useState([emptyItem()])
  const canCreate = usePermission(VENTAS_PERMISSIONS.crear)
  const canEdit = usePermission(VENTAS_PERMISSIONS.editar)
  const canSubmit = isEdit ? canEdit : canCreate
  const noPermissionMessage = isEdit
    ? 'No tiene permiso para editar facturas de venta.'
    : 'No tiene permiso para crear facturas de venta.'

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [clientesRows, pedidosRows, guiasRows, productosRows, impuestosRows] = await Promise.all([
        ventasApi.getList('/clientes/'),
        ventasApi.getList(ventasApi.endpoints.pedidos),
        ventasApi.getList(ventasApi.endpoints.guias),
        ventasApi.getList('/productos/'),
        ventasApi.getList('/impuestos/'),
      ])
      setClientes(clientesRows)
      setPedidos(pedidosRows)
      setGuias(guiasRows)
      setProductos(productosRows)
      setImpuestos(impuestosRows)

      if (isEdit) {
        const factura = await ventasApi.getOne(ventasApi.endpoints.facturas, id)
        const itemRows = await ventasApi.getList(ventasApi.endpoints.facturasItems)
        const scoped = itemRows.filter((row) => String(row.factura_venta) === String(id))
        setNumeroPreview(String(factura.numero || '-'))
        setForm({
          cliente: String(factura.cliente || ''),
          pedido_venta: factura.pedido_venta ? String(factura.pedido_venta) : '',
          guia_despacho: factura.guia_despacho ? String(factura.guia_despacho) : '',
          fecha_emision: factura.fecha_emision || getChileDateSuffix(),
          fecha_vencimiento: factura.fecha_vencimiento || getChileDateSuffix(),
          observaciones: factura.observaciones || '',
        })
        setItems(scoped.length ? scoped.map((row) => ({
          producto: String(row.producto || ''),
          descripcion: row.descripcion || '',
          cantidad: toQuantityString(row.cantidad || 1),
          precio_unitario: toIntegerString(row.precio_unitario || 0),
          descuento: toIntegerString(row.descuento || 0),
          impuesto: row.impuesto ? String(row.impuesto) : '',
          impuesto_porcentaje: toIntegerString(row.impuesto_porcentaje || 0),
        })) : [emptyItem()])
      } else {
        const next = await ventasApi.getOne(ventasApi.endpoints.facturas, 'siguiente_numero')
        setNumeroPreview(String(next?.numero || '-'))
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el formulario de factura.' }))
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
  const updateItem = (index, key, value) => {
    setItems((prev) => {
      const next = [...prev]
      const row = { ...next[index], [key]: value }
      if (key === 'producto') {
        const found = productos.find((p) => String(p.id) === String(value))
        if (found) {
          row.descripcion = found.nombre || ''
          row.precio_unitario = toIntegerString(found.precio_referencia || 0)
          row.impuesto = found.impuesto ? String(found.impuesto) : ''
        }
      }
      next[index] = row
      return next
    })
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!canSubmit) {
      toast.error(noPermissionMessage)
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
        const gross = Number(row.cantidad || 0) * Number(row.precio_unitario || 0)
        const discount = gross * (Number(row.descuento || 0) / 100)
        const subtotal = gross - discount
        const tax = Number(row.impuesto_porcentaje || 0)
        return { subtotal, total: subtotal + subtotal * (tax / 100) }
      })
      const subtotal = totals.reduce((acc, row) => acc + row.subtotal, 0)
      const total = totals.reduce((acc, row) => acc + row.total, 0)

      const payload = {
        cliente: form.cliente,
        pedido_venta: form.pedido_venta || null,
        guia_despacho: form.guia_despacho || null,
        fecha_emision: form.fecha_emision,
        fecha_vencimiento: form.fecha_vencimiento,
        observaciones: form.observaciones || '',
        subtotal,
        impuestos: total - subtotal,
        total,
      }

      let recordId = id
      if (isEdit) {
        await ventasApi.updateOne(ventasApi.endpoints.facturas, id, payload)
        const existing = await ventasApi.getList(ventasApi.endpoints.facturasItems)
        const scoped = existing.filter((row) => String(row.factura_venta) === String(id))
        await Promise.all(scoped.map((row) => ventasApi.removeOne(ventasApi.endpoints.facturasItems, row.id)))
      } else {
        const created = await ventasApi.createOne(ventasApi.endpoints.facturas, payload)
        recordId = created.id
      }

      await Promise.all(items.map((row, index) => ventasApi.createOne(ventasApi.endpoints.facturasItems, {
        factura_venta: recordId,
        guia_item: null,
        producto: row.producto,
        descripcion: row.descripcion,
        cantidad: Number(row.cantidad),
        precio_unitario: Number(row.precio_unitario),
        descuento: Number(row.descuento || 0),
        impuesto: row.impuesto || null,
        impuesto_porcentaje: Number(row.impuesto_porcentaje || 0),
        subtotal: totals[index].subtotal,
        total: totals[index].total,
      })))

      toast.success(isEdit ? 'Factura actualizada.' : 'Factura creada.')
      navigate('/ventas/facturas')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la factura.' }))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-sm text-muted-foreground">Cargando formulario...</p>

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">{isEdit ? 'Editar factura' : 'Nueva factura de venta'}</h2>
          <p className="text-sm text-muted-foreground">Folio: {numeroPreview}</p>
        </div>
        <Link to="/ventas/facturas" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
      </div>

      {!canSubmit ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {noPermissionMessage}
        </p>
      ) : null}

      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-3">
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
          <select value={form.guia_despacho} onChange={(e) => updateForm('guia_despacho', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="">Guia (opcional)</option>
            {guias.map((row) => <option key={row.id} value={row.id}>{row.numero || row.id}</option>)}
          </select>
          <input type="date" value={form.fecha_emision} onChange={(e) => updateForm('fecha_emision', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input type="date" value={form.fecha_vencimiento} onChange={(e) => updateForm('fecha_vencimiento', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input value={form.observaciones} onChange={(e) => updateForm('observaciones', e.target.value)} placeholder="Observaciones" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
        </div>

        <div className="space-y-2 rounded-md border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Items</h3>
            <Button type="button" variant="outline" size="sm" onClick={() => setItems((prev) => [...prev, emptyItem()])}>Agregar item</Button>
          </div>
          {items.map((row, index) => (
            <div key={`item-${index}`} className="grid gap-2 rounded-md border border-border p-3 md:grid-cols-6">
              <SearchableSelect
                value={row.producto}
                onChange={(v) => updateItem(index, 'producto', v)}
                options={productoOptions}
                placeholder="Buscar producto..."
                ariaLabel={`Producto item ${index + 1}`}
              />
              <input value={row.descripcion} onChange={(e) => updateItem(index, 'descripcion', e.target.value)} placeholder="Descripcion" className="rounded-md border border-border bg-background px-2 py-2 text-sm md:col-span-2" />
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
          <Link to="/ventas/facturas" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Cancelar</Link>
          <Button type="submit" disabled={saving || !canSubmit}>{saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear factura'}</Button>
        </div>
      </form>
    </section>
  )
}

export default VentasFacturasFormPage
