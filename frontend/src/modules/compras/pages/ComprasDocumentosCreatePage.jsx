import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { getProductosCatalog } from '@/modules/productos/services/productosCatalogCache'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function todayDate() {
  return new Date().toISOString().slice(0, 10)
}

const EMPTY_ITEM = {
  producto: '',
  descripcion: '',
  cantidad: '1',
  precio_unitario: '0',
  descuento: '0',
  subtotal: '0',
}

function calcSubtotal(item) {
  const cant = Number(item.cantidad) || 0
  const precio = Number(item.precio_unitario) || 0
  const descuento = Math.min(Math.max(Number(item.descuento) || 0, 0), 100)
  return Math.round(cant * precio * (1 - descuento / 100))
}

function ComprasDocumentosCreatePage() {
  const navigate = useNavigate()
  const { id: documentoId } = useParams()
  const [searchParams] = useSearchParams()
  const isEditMode = Boolean(documentoId)
  const prefillAppliedRef = useRef(false)

  const [proveedores, setProveedores] = useState([])
  const [ordenesCompra, setOrdenesCompra] = useState([])
  const [contactos, setContactos] = useState([])
  const [productos, setProductos] = useState([])
  const [saving, setSaving] = useState(false)
  const [loadingEdit, setLoadingEdit] = useState(isEditMode)

  const [form, setForm] = useState({
    tipo_documento: 'GUIA_RECEPCION',
    proveedor: '',
    orden_compra: '',
    folio: '',
    serie: '',
    fecha_emision: todayDate(),
    fecha_recepcion: todayDate(),
    observaciones: '',
  })

  const [items, setItems] = useState([{ ...EMPTY_ITEM }])

  useEffect(() => {
    const loadBase = async () => {
      try {
        const [{ data: provData }, { data: ctcData }, { data: ordenesData }, productosData] = await Promise.all([
          api.get('/proveedores/', { suppressGlobalErrorToast: true }),
          api.get('/contactos/', { suppressGlobalErrorToast: true }),
          api.get('/ordenes-compra/', { suppressGlobalErrorToast: true }),
          getProductosCatalog(),
        ])
        setProveedores(normalizeListResponse(provData))
        setContactos(normalizeListResponse(ctcData))
        setOrdenesCompra(normalizeListResponse(ordenesData))
        setProductos(productosData)
      } catch {
        toast.error('No se pudieron cargar los datos base.')
      }
    }

    void loadBase()
  }, [])

  useEffect(() => {
    if (!isEditMode) return

    const loadForEdit = async () => {
      setLoadingEdit(true)
      try {
        const [{ data: doc }, { data: itemsData }] = await Promise.all([
          api.get(`/documentos-compra/${documentoId}/`, { suppressGlobalErrorToast: true }),
          api.get(`/documentos-compra-items/?documento=${documentoId}`, { suppressGlobalErrorToast: true }),
        ])

        setForm({
          tipo_documento: doc.tipo_documento || 'GUIA_RECEPCION',
          proveedor: String(doc.proveedor || ''),
          orden_compra: doc.orden_compra ? String(doc.orden_compra) : '',
          folio: doc.folio || '',
          serie: doc.serie || '',
          fecha_emision: doc.fecha_emision || todayDate(),
          fecha_recepcion: doc.fecha_recepcion || todayDate(),
          observaciones: doc.observaciones || '',
        })

        const loaded = normalizeListResponse(itemsData)
        setItems(
          loaded.length > 0
            ? loaded.map((it) => ({
                _id: it.id,
                producto: String(it.producto || ''),
                descripcion: it.descripcion || '',
                cantidad: String(it.cantidad || 1),
                precio_unitario: String(it.precio_unitario || 0),
                descuento: String(it.descuento || 0),
                subtotal: String(it.subtotal || 0),
              }))
            : [{ ...EMPTY_ITEM }],
        )
      } catch {
        toast.error('No se pudo cargar el documento para editar.')
      } finally {
        setLoadingEdit(false)
      }
    }

    void loadForEdit()
  }, [isEditMode, documentoId])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((c) => map.set(String(c.id), c))
    return map
  }, [contactos])

  const proveedorOptions = useMemo(
    () =>
      proveedores.map((prov) => {
        const ctc = contactoById.get(String(prov.contacto))
        return {
          value: String(prov.id),
          label: ctc?.nombre || `Proveedor ${prov.id}`,
          keywords: `${ctc?.rut || ''} ${ctc?.email || ''}`,
        }
      }),
    [proveedores, contactoById],
  )

  const ordenesDisponibles = useMemo(
    () =>
      ordenesCompra.filter(
        (orden) =>
          String(orden.proveedor || '') === String(form.proveedor || '') &&
          String(orden.estado || '').toUpperCase() !== 'CANCELADA',
      ),
    [ordenesCompra, form.proveedor],
  )

  const ordenCompraOptions = useMemo(
    () =>
      ordenesDisponibles.map((orden) => ({
        value: String(orden.id),
        label: `${orden.numero || 'OC'} - ${orden.fecha_emision || '-'}`,
        keywords: `${orden.estado || ''} ${orden.observaciones || ''}`,
      })),
    [ordenesDisponibles],
  )

  const productoOptions = useMemo(
    () =>
      productos
        .filter((p) => String(p.tipo || '').toUpperCase() === 'PRODUCTO')
        .map((p) => ({
        value: String(p.id),
        label: p.nombre || `Producto ${p.id}`,
        keywords: `${p.sku || ''} ${p.tipo || ''}`,
      })),
    [productos],
  )

  const productoById = useMemo(() => {
    const map = new Map()
    productos.forEach((p) => map.set(String(p.id), p))
    return map
  }, [productos])

  const handleFormChange = (field, value) => {
    if (field === 'proveedor') {
      setForm((prev) => ({ ...prev, proveedor: value, orden_compra: '' }))
      return
    }

    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const applyOrdenCompraToForm = async (ordenCompraId) => {
    const nextId = String(ordenCompraId || '')
    setForm((prev) => ({ ...prev, orden_compra: nextId }))

    if (!nextId) {
      return
    }

    const orden = ordenesCompra.find((row) => String(row.id) === nextId)
    if (!orden) {
      return
    }

    setForm((prev) => ({
      ...prev,
      proveedor: String(orden.proveedor || prev.proveedor || ''),
      fecha_emision: prev.fecha_emision || todayDate(),
      observaciones: prev.observaciones || orden.observaciones || '',
      orden_compra: nextId,
    }))

    try {
      const { data: itemsData } = await api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true })
      const ocItems = normalizeListResponse(itemsData).filter((row) => String(row.orden_compra) === nextId)
      if (ocItems.length > 0) {
        setItems(
          ocItems.map((item) => ({
            producto: String(item.producto || ''),
            descripcion: item.descripcion || '',
            cantidad: String(item.cantidad || '1'),
            precio_unitario: String(item.precio_unitario || '0'),
            descuento: '0',
            subtotal: String(Math.round(Number(item.subtotal || 0))),
          })),
        )
      }
    } catch {
      toast.error('No se pudieron cargar los items de la orden de compra seleccionada.')
    }
  }

  useEffect(() => {
    if (isEditMode || prefillAppliedRef.current) {
      return
    }

    const ordenPrefillId = searchParams.get('orden_compra')
    if (!ordenPrefillId || ordenesCompra.length === 0) {
      return
    }

    prefillAppliedRef.current = true
    void applyOrdenCompraToForm(ordenPrefillId)
  }, [isEditMode, searchParams, ordenesCompra])

  const handleItemChange = (index, field, value) => {
    setItems((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], [field]: value }

      if (field === 'producto') {
        const selected = productoById.get(String(value))
        if (selected) {
          next[index].descripcion = selected.nombre || next[index].descripcion
          if (!Number(next[index].precio_unitario || 0)) {
            next[index].precio_unitario = String(Math.round(Number(selected.precio_referencia || 0)))
          }
          next[index].subtotal = String(calcSubtotal(next[index]))
        }
      }

      if (field === 'cantidad' || field === 'precio_unitario' || field === 'descuento') {
        next[index].subtotal = String(calcSubtotal(next[index]))
      }
      return next
    })
  }

  const addItem = () => setItems((prev) => [...prev, { ...EMPTY_ITEM }])

  const removeItem = (index) => {
    if (items.length === 1) return
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const subtotalNeto = useMemo(() => items.reduce((acc, it) => acc + (Number(it.subtotal) || 0), 0), [items])

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.proveedor) {
      toast.error('Debe seleccionar un proveedor.')
      return
    }
    if (!form.folio.trim()) {
      toast.error('El folio es obligatorio.')
      return
    }
    if (items.some((it) => !it.producto)) {
      toast.error('Todos los items deben tener producto.')
      return
    }

    setSaving(true)
    try {
      // Calcular totales
      const iva = Math.round(subtotalNeto * 0.19)
      const total = subtotalNeto + iva

      const docPayload = {
        tipo_documento: form.tipo_documento,
        proveedor: form.proveedor,
        orden_compra: form.orden_compra || null,
        folio: form.folio.trim(),
        serie: form.serie.trim(),
        fecha_emision: form.fecha_emision,
        fecha_recepcion: form.fecha_recepcion,
        observaciones: form.observaciones.trim(),
        subtotal_neto: subtotalNeto,
        impuestos: iva,
        total,
      }

      let docId = documentoId

      if (isEditMode) {
        await api.patch(`/documentos-compra/${documentoId}/`, docPayload)

        // Delete existing items and re-create
        const { data: existingItems } = await api.get(`/documentos-compra-items/?documento=${documentoId}`, {
          suppressGlobalErrorToast: true,
        })
        await Promise.all(
          normalizeListResponse(existingItems).map((it) => api.delete(`/documentos-compra-items/${it.id}/`)),
        )
      } else {
        const { data: newDoc } = await api.post('/documentos-compra/', docPayload)
        docId = newDoc.id
      }

      await Promise.all(
        items.map((it) =>
          api.post('/documentos-compra-items/', {
            documento: docId,
            producto: it.producto,
            descripcion: it.descripcion,
            cantidad: Number(it.cantidad),
            precio_unitario: Number(it.precio_unitario),
            descuento: Number(it.descuento),
            subtotal: Number(it.subtotal),
          }),
        ),
      )

      toast.success(isEditMode ? 'Documento actualizado.' : 'Documento creado.')
      navigate('/compras/documentos')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar el documento.' }))
    } finally {
      setSaving(false)
    }
  }

  if (loadingEdit) {
    return <p className="text-sm text-muted-foreground">Cargando documento...</p>
  }

  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-semibold">{isEditMode ? 'Editar documento de compra' : 'Nuevo documento de compra'}</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Header */}
        <div className="rounded-md border border-border bg-card p-4 space-y-4">
          <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">Datos del documento</h3>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Tipo de documento</label>
              <select
                value={form.tipo_documento}
                onChange={(e) => handleFormChange('tipo_documento', e.target.value)}
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="GUIA_RECEPCION">Guía de recepción</option>
                <option value="FACTURA_COMPRA">Factura de compra</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Proveedor</label>
              <SearchableSelect
                className="mt-1"
                value={form.proveedor}
                onChange={(next) => handleFormChange('proveedor', next)}
                options={proveedorOptions}
                ariaLabel="Proveedor"
                placeholder="Buscar proveedor..."
                emptyText="No hay proveedores coincidentes"
                disabled={Boolean(form.orden_compra)}
              />
              {form.orden_compra ? (
                <p className="mt-1 text-xs text-muted-foreground">Proveedor bloqueado por OC seleccionada.</p>
              ) : null}
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Orden de compra (opcional)</label>
              <SearchableSelect
                className="mt-1"
                value={form.orden_compra}
                onChange={(next) => {
                  void applyOrdenCompraToForm(next)
                }}
                options={ordenCompraOptions}
                ariaLabel="Orden de compra"
                placeholder={form.proveedor ? 'Seleccionar OC...' : 'Primero seleccione proveedor'}
                emptyText="No hay OCs disponibles para este proveedor"
                disabled={!form.proveedor}
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Folio</label>
              <input
                type="text"
                value={form.folio}
                onChange={(e) => handleFormChange('folio', e.target.value)}
                placeholder="Ej: 123456"
                required
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Serie (opcional)</label>
              <input
                type="text"
                value={form.serie}
                onChange={(e) => handleFormChange('serie', e.target.value)}
                placeholder="Ej: A"
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Fecha de emisión</label>
              <input
                type="date"
                value={form.fecha_emision}
                onChange={(e) => handleFormChange('fecha_emision', e.target.value)}
                required
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Fecha de recepción</label>
              <input
                type="date"
                value={form.fecha_recepcion}
                onChange={(e) => handleFormChange('fecha_recepcion', e.target.value)}
                required
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium">Observaciones</label>
            <textarea
              value={form.observaciones}
              onChange={(e) => handleFormChange('observaciones', e.target.value)}
              rows={2}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="Observaciones opcionales..."
            />
          </div>
        </div>

        {/* Items */}
        <div className="rounded-md border border-border bg-card p-4 space-y-4">
          <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide">Detalle de productos</h3>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  <th className="px-2 py-2 text-left font-medium">Producto</th>
                  <th className="px-2 py-2 text-left font-medium">Descripción</th>
                  <th className="px-2 py-2 text-right font-medium w-24">Cantidad</th>
                  <th className="px-2 py-2 text-right font-medium w-28">Precio unit.</th>
                  <th className="px-2 py-2 text-right font-medium w-20">Desc. %</th>
                  <th className="px-2 py-2 text-right font-medium w-28">Subtotal</th>
                  <th className="px-2 py-2 w-10" />
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={index} className="border-t border-border">
                    <td className="px-2 py-1">
                      <SearchableSelect
                        inputClassName="px-2 py-1"
                        value={item.producto}
                        onChange={(next) => handleItemChange(index, 'producto', next)}
                        options={productoOptions}
                        ariaLabel="Producto"
                        placeholder="Buscar producto..."
                        emptyText="No hay productos coincidentes"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="text"
                        value={item.descripcion}
                        onChange={(e) => handleItemChange(index, 'descripcion', e.target.value)}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm"
                        placeholder="Descripción..."
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={item.cantidad}
                        onChange={(e) => handleItemChange(index, 'cantidad', e.target.value)}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm text-right"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={item.precio_unitario}
                        onChange={(e) => handleItemChange(index, 'precio_unitario', e.target.value)}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm text-right"
                      />
                    </td>
                    <td className="px-2 py-1">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={item.descuento}
                        onChange={(e) => handleItemChange(index, 'descuento', e.target.value)}
                        className="w-full rounded border border-input bg-background px-2 py-1 text-sm text-right"
                      />
                    </td>
                    <td className="px-2 py-1 text-right font-medium">
                      {Number(item.subtotal).toLocaleString('es-CL')}
                    </td>
                    <td className="px-2 py-1 text-center">
                      <button
                        type="button"
                        onClick={() => removeItem(index)}
                        disabled={items.length === 1}
                        className="text-destructive hover:opacity-70 disabled:opacity-30"
                        aria-label="Eliminar item"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Button type="button" variant="outline" size="sm" onClick={addItem}>
            + Agregar ítem
          </Button>
        </div>

        {/* Totals summary */}
        <div className="flex justify-end">
          <div className="w-full max-w-xs space-y-1 rounded-md border border-border bg-card p-4 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Subtotal neto</span>
              <span>{subtotalNeto.toLocaleString('es-CL')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">IVA (19%)</span>
              <span>{Math.round(subtotalNeto * 0.19).toLocaleString('es-CL')}</span>
            </div>
            <div className="flex justify-between font-semibold border-t border-border pt-1">
              <span>Total</span>
              <span>{Math.round(subtotalNeto * 1.19).toLocaleString('es-CL')}</span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 justify-end">
          <Button type="button" variant="outline" size="md" onClick={() => navigate('/compras/documentos')}>
            Cancelar
          </Button>
          <Button type="submit" variant="default" size="md" disabled={saving}>
            {saving ? 'Guardando...' : isEditMode ? 'Guardar cambios' : 'Crear documento'}
          </Button>
        </div>
      </form>
    </section>
  )
}

export default ComprasDocumentosCreatePage
