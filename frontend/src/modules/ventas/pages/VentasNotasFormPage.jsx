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
  return { factura_item: '', producto: '', descripcion: '', cantidad: '1', precio_unitario: '0', descuento: '0', impuesto: '', impuesto_porcentaje: '0' }
}

function VentasNotasFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [numeroPreview, setNumeroPreview] = useState('...')
  const [clientes, setClientes] = useState([])
  const [facturas, setFacturas] = useState([])
  const [facturaItems, setFacturaItems] = useState([])
  const [productos, setProductos] = useState([])
  const [form, setForm] = useState({ cliente: '', factura_venta: '', fecha_emision: getChileDateSuffix(), motivo: '', observaciones: '' })
  const [items, setItems] = useState([emptyItem()])
  const canCreate = usePermission(VENTAS_PERMISSIONS.crear)
  const canEdit = usePermission(VENTAS_PERMISSIONS.editar)
  const canSubmit = isEdit ? canEdit : canCreate
  const noPermissionMessage = isEdit
    ? 'No tiene permiso para editar notas de credito.'
    : 'No tiene permiso para crear notas de credito.'

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [clientesRows, facturasRows, facturaItemsRows, productosRows] = await Promise.all([
        ventasApi.getList('/clientes/'),
        ventasApi.getList(ventasApi.endpoints.facturas),
        ventasApi.getList(ventasApi.endpoints.facturasItems),
        ventasApi.getList('/productos/'),
      ])
      setClientes(clientesRows)
      setFacturas(facturasRows)
      setFacturaItems(facturaItemsRows)
      setProductos(productosRows)

      if (isEdit) {
        const nota = await ventasApi.getOne(ventasApi.endpoints.notas, id)
        const itemRows = await ventasApi.getList(ventasApi.endpoints.notasItems)
        const scoped = itemRows.filter((row) => String(row.nota_credito_venta) === String(id))
        setNumeroPreview(String(nota.numero || '-'))
        setForm({
          cliente: String(nota.cliente || ''),
          factura_venta: String(nota.factura_venta || ''),
          fecha_emision: nota.fecha_emision || getChileDateSuffix(),
          motivo: nota.motivo || '',
          observaciones: nota.observaciones || '',
        })
        setItems(scoped.length ? scoped.map((row) => ({
          factura_item: row.factura_item ? String(row.factura_item) : '',
          producto: String(row.producto || ''),
          descripcion: row.descripcion || '',
          cantidad: toQuantityString(row.cantidad || 1),
          precio_unitario: toIntegerString(row.precio_unitario || 0),
          descuento: toIntegerString(row.descuento || 0),
          impuesto: row.impuesto ? String(row.impuesto) : '',
          impuesto_porcentaje: toIntegerString(row.impuesto_porcentaje || 0),
        })) : [emptyItem()])
      } else {
        const next = await ventasApi.getOne(ventasApi.endpoints.notas, 'siguiente_numero')
        setNumeroPreview(String(next?.numero || '-'))
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el formulario de nota de credito.' }))
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

  const updateForm = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    if (key === 'factura_venta') {
      setItems([emptyItem()])
    }
  }

  const updateItem = (index, key, value) => {
    setItems((prev) => {
      const next = [...prev]
      const row = { ...next[index], [key]: value }
      if (key === 'factura_item') {
        const found = facturaItems.find((item) => String(item.id) === String(value))
        if (found) {
          row.producto = String(found.producto || '')
          row.descripcion = found.descripcion || ''
          row.precio_unitario = toIntegerString(found.precio_unitario || 0)
          row.impuesto = found.impuesto ? String(found.impuesto) : ''
          row.impuesto_porcentaje = toIntegerString(found.impuesto_porcentaje || 0)
          row.cantidad = toQuantityString(found.cantidad || 1)
        }
      }
      if (key === 'producto') {
        const product = productos.find((item) => String(item.id) === String(value))
        if (product) {
          row.descripcion = row.descripcion || product.nombre || ''
          row.precio_unitario = toIntegerString(product.precio_referencia || 0)
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
    if (!form.cliente || !form.factura_venta) {
      toast.error('Seleccione cliente y factura.')
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
        factura_venta: form.factura_venta,
        fecha_emision: form.fecha_emision,
        motivo: form.motivo,
        observaciones: form.observaciones || '',
        subtotal,
        impuestos: total - subtotal,
        total,
      }

      let recordId = id
      if (isEdit) {
        await ventasApi.updateOne(ventasApi.endpoints.notas, id, payload)
        const existing = await ventasApi.getList(ventasApi.endpoints.notasItems)
        const scoped = existing.filter((row) => String(row.nota_credito_venta) === String(id))
        await Promise.all(scoped.map((row) => ventasApi.removeOne(ventasApi.endpoints.notasItems, row.id)))
      } else {
        const created = await ventasApi.createOne(ventasApi.endpoints.notas, payload)
        recordId = created.id
      }

      await Promise.all(items.map((row, index) => ventasApi.createOne(ventasApi.endpoints.notasItems, {
        nota_credito_venta: recordId,
        factura_item: row.factura_item || null,
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

      toast.success(isEdit ? 'Nota de credito actualizada.' : 'Nota de credito creada.')
      navigate('/ventas/notas')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la nota de credito.' }))
    } finally {
      setSaving(false)
    }
  }

  const facturaItemsOptions = facturaItems.filter((row) => String(row.factura_venta) === String(form.factura_venta))

  if (loading) return <p className="text-sm text-muted-foreground">Cargando formulario...</p>

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">{isEdit ? 'Editar nota de credito' : 'Nueva nota de credito'}</h2>
          <p className="text-sm text-muted-foreground">Folio: {numeroPreview}</p>
        </div>
        <Link to="/ventas/notas" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
      </div>

      {!canSubmit ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {noPermissionMessage}
        </p>
      ) : null}

      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-2">
          <SearchableSelect
            value={form.cliente}
            onChange={(v) => updateForm('cliente', v)}
            options={clienteOptions}
            placeholder="Buscar cliente..."
            ariaLabel="Cliente"
          />
          <select value={form.factura_venta} onChange={(e) => updateForm('factura_venta', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm">
            <option value="">Factura</option>
            {facturas.map((row) => <option key={row.id} value={row.id}>{row.numero || row.id}</option>)}
          </select>
          <input type="date" value={form.fecha_emision} onChange={(e) => updateForm('fecha_emision', e.target.value)} className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input value={form.motivo} onChange={(e) => updateForm('motivo', e.target.value)} placeholder="Motivo" className="rounded-md border border-border bg-background px-3 py-2 text-sm" />
          <input value={form.observaciones} onChange={(e) => updateForm('observaciones', e.target.value)} placeholder="Observaciones" className="rounded-md border border-border bg-background px-3 py-2 text-sm md:col-span-2" />
        </div>

        <div className="space-y-2 rounded-md border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Items de nota</h3>
            <Button type="button" variant="outline" size="sm" onClick={() => setItems((prev) => [...prev, emptyItem()])}>Agregar item</Button>
          </div>
          {items.map((row, index) => (
            <div key={`item-${index}`} className="grid gap-2 rounded-md border border-border p-3 md:grid-cols-6">
              <select value={row.factura_item} onChange={(e) => updateItem(index, 'factura_item', e.target.value)} className="rounded-md border border-border bg-background px-2 py-2 text-sm">
                <option value="">Item factura</option>
                {facturaItemsOptions.map((item) => <option key={item.id} value={item.id}>{item.descripcion || item.id}</option>)}
              </select>
              <SearchableSelect
                value={row.producto}
                onChange={(v) => updateItem(index, 'producto', v)}
                options={productoOptions}
                placeholder="Buscar producto..."
                ariaLabel={`Producto item ${index + 1}`}
              />
              <input value={row.descripcion} onChange={(e) => updateItem(index, 'descripcion', e.target.value)} placeholder="Descripcion" className="rounded-md border border-border bg-background px-2 py-2 text-sm md:col-span-2" />
              <input value={row.cantidad} onChange={(e) => updateItem(index, 'cantidad', toQuantityString(e.target.value))} placeholder="Cantidad" className="rounded-md border border-border bg-background px-2 py-2 text-sm" />
              <div className="flex gap-2">
                <input value={row.precio_unitario} onChange={(e) => updateItem(index, 'precio_unitario', toIntegerString(e.target.value))} placeholder="Precio" className="min-w-0 flex-1 rounded-md border border-border bg-background px-2 py-2 text-sm" />
                <Button type="button" variant="destructive" size="sm" onClick={() => setItems((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)))}>Quitar</Button>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2">
          <Link to="/ventas/notas" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Cancelar</Link>
          <Button type="submit" disabled={saving || !canSubmit}>{saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear nota'}</Button>
        </div>
      </form>
    </section>
  )
}

export default VentasNotasFormPage
