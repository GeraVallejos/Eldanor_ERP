import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
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
  return {
    producto: '',
    descripcion: '',
    cantidad: '1',
    precio_unitario: '0',
    descuento: '0',
    impuesto: '',
    impuesto_porcentaje: '0',
    presupuesto_item_origen: '',
  }
}

function today() {
  return getChileDateSuffix()
}

function VentasPedidosFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const presupuestoId = searchParams.get('presupuesto') || ''
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [clientes, setClientes] = useState([])
  const [productos, setProductos] = useState([])
  const [impuestos, setImpuestos] = useState([])
  const [numeroPreview, setNumeroPreview] = useState('...')
  const [presupuestoOrigenId, setPresupuestoOrigenId] = useState('')
  const [form, setForm] = useState({
    cliente: '',
    fecha_emision: today(),
    fecha_entrega: '',
    observaciones: '',
    descuento: '0',
  })
  const [items, setItems] = useState([emptyItem()])
  const canCreate = usePermission(VENTAS_PERMISSIONS.crear)
  const canEdit = usePermission(VENTAS_PERMISSIONS.editar)
  const canSubmit = isEdit ? canEdit : canCreate
  const noPermissionMessage = isEdit
    ? 'No tiene permiso para editar pedidos de venta.'
    : 'No tiene permiso para crear pedidos de venta.'

  const loadInitial = useCallback(async () => {
    setLoading(true)
    try {
      const [clientesRows, productosRows, impuestosRows] = await Promise.all([
        ventasApi.getList('/clientes/'),
        ventasApi.getList('/productos/'),
        ventasApi.getList('/impuestos/'),
      ])

      setClientes(clientesRows)
      setProductos(productosRows)
      setImpuestos(impuestosRows)

      if (isEdit) {
        const pedido = await ventasApi.getOne(ventasApi.endpoints.pedidos, id)
        const itemsRows = await ventasApi.getList(ventasApi.endpoints.pedidosItems)
        const scopedItems = itemsRows.filter((row) => String(row.pedido_venta) === String(id))

        setForm({
          cliente: String(pedido.cliente || ''),
          fecha_emision: pedido.fecha_emision || today(),
          fecha_entrega: pedido.fecha_entrega || '',
          observaciones: pedido.observaciones || '',
          descuento: toIntegerString(pedido.descuento || 0),
        })
        setNumeroPreview(String(pedido.numero || '-'))
        setPresupuestoOrigenId(String(pedido.presupuesto_origen || ''))
        setItems(
          scopedItems.length > 0
            ? scopedItems.map((row) => ({
                producto: String(row.producto || ''),
                descripcion: row.descripcion || '',
                cantidad: toQuantityString(row.cantidad || 1),
                precio_unitario: toIntegerString(row.precio_unitario || 0),
                descuento: toIntegerString(row.descuento || 0),
                impuesto: row.impuesto ? String(row.impuesto) : '',
                impuesto_porcentaje: toIntegerString(row.impuesto_porcentaje || 0),
                presupuesto_item_origen: row.presupuesto_item_origen ? String(row.presupuesto_item_origen) : '',
              }))
            : [emptyItem()],
        )
      } else {
        const next = await ventasApi.getOne(ventasApi.endpoints.pedidos, 'siguiente_numero')
        setNumeroPreview(String(next?.numero || '-'))
        if (presupuestoId) {
          const [{ data: presupuesto }, { data: trazabilidad }] = await Promise.all([
            api.get(`/presupuestos/${presupuestoId}/`, { suppressGlobalErrorToast: true }),
            api.get(`/presupuestos/${presupuestoId}/trazabilidad/`, { suppressGlobalErrorToast: true }),
          ])
          const presupuestoItems = Array.isArray(trazabilidad?.consumo?.items)
            ? trazabilidad.consumo.items.filter((row) => Number(row.cantidad_disponible || 0) > 0)
            : []
          setPresupuestoOrigenId(String(presupuesto.id))
          setForm({
            cliente: String(presupuesto.cliente || ''),
            fecha_emision: presupuesto.fecha || today(),
            fecha_entrega: presupuesto.fecha_vencimiento || '',
            observaciones: presupuesto.observaciones || '',
            descuento: toIntegerString(presupuesto.descuento || 0),
          })
          setItems(
            presupuestoItems.length > 0
              ? presupuestoItems.map((row) => ({
                  producto: String(row.producto_id || row.producto || ''),
                  descripcion: row.descripcion || '',
                  cantidad: toQuantityString(row.cantidad_disponible || row.cantidad || 1),
                  precio_unitario: toIntegerString(row.precio_unitario || 0),
                  descuento: toIntegerString(row.descuento || 0),
                  impuesto: row.impuesto ? String(row.impuesto) : '',
                  impuesto_porcentaje: toIntegerString(row.impuesto_porcentaje || 0),
                  presupuesto_item_origen: String(row.id),
                }))
              : [emptyItem()],
          )
        }
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos del formulario.' }))
    } finally {
      setLoading(false)
    }
  }, [id, isEdit, presupuestoId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadInitial()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [loadInitial])

  const impuestoById = useMemo(() => {
    const map = new Map()
    impuestos.forEach((row) => map.set(String(row.id), row))
    return map
  }, [impuestos])

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
        const product = productos.find((p) => String(p.id) === String(value))
        if (product) {
          row.descripcion = product.nombre || ''
          row.precio_unitario = toIntegerString(product.precio_referencia || 0)
          row.impuesto = product.impuesto ? String(product.impuesto) : ''
        }
      }
      next[index] = row
      return next
    })
  }

  const addItem = () => setItems((prev) => [...prev, emptyItem()])
  const removeItem = (index) => setItems((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)))

  const computeTotals = (row) => {
    const qty = Number(row.cantidad || 0)
    const price = Number(row.precio_unitario || 0)
    const descPct = Number(row.descuento || 0)
    const taxPct = Number(row.impuesto_porcentaje || impuestoById.get(String(row.impuesto))?.porcentaje || 0)

    const gross = qty * price
    const discount = gross * (descPct / 100)
    const subtotal = gross - discount
    const total = subtotal + subtotal * (taxPct / 100)
    return { subtotal, total }
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!canSubmit) {
      toast.error(noPermissionMessage)
      return
    }
    if (!form.cliente) {
      toast.error('Debe seleccionar un cliente.')
      return
    }

    const invalidItem = items.some((row) => !row.producto || Number(row.cantidad) <= 0)
    if (invalidItem) {
      toast.error('Revise los items del pedido.')
      return
    }

    setSaving(true)
    try {
      const totals = items.map(computeTotals)
      const subtotal = totals.reduce((acc, row) => acc + row.subtotal, 0)
      const total = totals.reduce((acc, row) => acc + row.total, 0)
      const payload = {
        cliente: form.cliente,
        presupuesto_origen: presupuestoOrigenId || null,
        fecha_emision: form.fecha_emision,
        fecha_entrega: form.fecha_entrega || null,
        observaciones: form.observaciones || '',
        descuento: Number(form.descuento || 0),
        subtotal,
        impuestos: total - subtotal,
        total,
      }

      let pedidoId = id
      if (isEdit) {
        await ventasApi.updateOne(ventasApi.endpoints.pedidos, id, payload)
        const existing = await ventasApi.getList(ventasApi.endpoints.pedidosItems)
        const scoped = existing.filter((row) => String(row.pedido_venta) === String(id))
        await Promise.all(scoped.map((row) => ventasApi.removeOne(ventasApi.endpoints.pedidosItems, row.id)))
      } else {
        const created = await ventasApi.createOne(ventasApi.endpoints.pedidos, payload)
        pedidoId = created.id
      }

      await Promise.all(
        items.map((row, index) => {
          const rowTotals = totals[index]
          return ventasApi.createOne(ventasApi.endpoints.pedidosItems, {
            pedido_venta: pedidoId,
            producto: row.producto,
            descripcion: row.descripcion,
            cantidad: Number(row.cantidad),
            precio_unitario: Number(row.precio_unitario),
            descuento: Number(row.descuento || 0),
            impuesto: row.impuesto || null,
            impuesto_porcentaje: Number(row.impuesto_porcentaje || impuestoById.get(String(row.impuesto))?.porcentaje || 0),
            presupuesto_item_origen: row.presupuesto_item_origen || null,
            subtotal: rowTotals.subtotal,
            total: rowTotals.total,
          })
        }),
      )

      toast.success(isEdit ? 'Pedido actualizado.' : 'Pedido creado.')
      navigate('/ventas/pedidos')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar el pedido.' }))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando formulario...</p>
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold">{isEdit ? 'Editar pedido' : 'Nuevo pedido de venta'}</h2>
          <p className="text-sm text-muted-foreground">Folio: {numeroPreview}</p>
          {!isEdit && presupuestoOrigenId ? (
            <p className="text-xs text-muted-foreground">Origen comercial: presupuesto {presupuestoOrigenId}</p>
          ) : null}
        </div>
        <Link to="/ventas/pedidos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
      </div>

      {!canSubmit ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {noPermissionMessage}
        </p>
      ) : null}

      <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-3 rounded-md border border-border bg-card p-4 md:grid-cols-2">
          <div className="space-y-1 text-sm">
            <span className="text-muted-foreground">Cliente</span>
            <SearchableSelect
              value={form.cliente}
              onChange={(v) => updateForm('cliente', v)}
              options={clienteOptions}
              placeholder="Buscar cliente..."
              ariaLabel="Cliente"
            />
          </div>

          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">Fecha emision</span>
            <input
              type="date"
              value={form.fecha_emision}
              onChange={(e) => updateForm('fecha_emision', e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2"
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">Fecha entrega</span>
            <input
              type="date"
              value={form.fecha_entrega}
              onChange={(e) => updateForm('fecha_entrega', e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2"
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">Descuento global (%)</span>
            <input
              value={form.descuento}
              onChange={(e) => updateForm('descuento', toIntegerString(e.target.value))}
              className="w-full rounded-md border border-border bg-background px-3 py-2"
            />
          </label>

          <label className="space-y-1 text-sm md:col-span-2">
            <span className="text-muted-foreground">Observaciones</span>
            <textarea
              value={form.observaciones}
              onChange={(e) => updateForm('observaciones', e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2"
              rows={3}
            />
          </label>
        </div>

        <div className="space-y-2 rounded-md border border-border bg-card p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">Items</h3>
            <Button type="button" variant="outline" size="sm" onClick={addItem}>Agregar item</Button>
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

              <input
                value={row.descripcion}
                onChange={(e) => updateItem(index, 'descripcion', e.target.value)}
                placeholder="Descripcion"
                className="rounded-md border border-border bg-background px-2 py-2 text-sm md:col-span-2"
              />
              <input
                value={row.cantidad}
                onChange={(e) => updateItem(index, 'cantidad', toQuantityString(e.target.value))}
                placeholder="Cantidad"
                className="rounded-md border border-border bg-background px-2 py-2 text-sm"
              />
              <input
                value={row.precio_unitario}
                onChange={(e) => updateItem(index, 'precio_unitario', toIntegerString(e.target.value))}
                placeholder="Precio"
                className="rounded-md border border-border bg-background px-2 py-2 text-sm"
              />
              <div className="flex gap-2">
                <select
                  value={row.impuesto}
                  onChange={(e) => updateItem(index, 'impuesto', e.target.value)}
                  className="min-w-0 flex-1 rounded-md border border-border bg-background px-2 py-2 text-sm"
                >
                  <option value="">IVA</option>
                  {impuestos.map((item) => (
                    <option key={item.id} value={item.id}>{item.nombre}</option>
                  ))}
                </select>
                <Button type="button" variant="destructive" size="sm" onClick={() => removeItem(index)}>Quitar</Button>
              </div>
              {row.presupuesto_item_origen ? (
                <p className="text-xs text-muted-foreground md:col-span-6">
                  Item vinculado al presupuesto origen.
                </p>
              ) : null}
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2">
          <Link to="/ventas/pedidos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Cancelar</Link>
          <Button type="submit" disabled={saving || !canSubmit}>{saving ? 'Guardando...' : isEdit ? 'Guardar cambios' : 'Crear pedido'}</Button>
        </div>
      </form>
    </section>
  )
}

export default VentasPedidosFormPage
