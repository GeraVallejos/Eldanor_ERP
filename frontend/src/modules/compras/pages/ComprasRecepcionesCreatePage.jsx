import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import SearchableSelect from '@/components/ui/SearchableSelect'
import { getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP, formatSmartNumber, toIntegerString } from '@/lib/numberFormat'
import { useNormalizedFormItems } from '@/hooks/useNormalizedFormItems'
import { getProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function todayDate() {
  return getChileDateSuffix()
}

const EMPTY_ITEM = {
  producto: '',
  orden_item: '',
  cantidad: '1',
  precio_unitario: '0',
}

function canCrearRecepcion(isEditMode, permissions) {
  return !isEditMode && permissions['COMPRAS.CREAR']
}

function canEditarRecepcion(isEditMode, recepcion, permissions) {
  return isEditMode && recepcion?.estado === 'BORRADOR' && permissions['COMPRAS.EDITAR']
}

function canConfirmarRecepcion(recepcion, permissions) {
  return recepcion?.estado === 'BORRADOR' && permissions['COMPRAS.APROBAR']
}

function ComprasRecepcionesCreatePage() {
  const navigate = useNavigate()
  const { id: recepcionId } = useParams()
  const [searchParams] = useSearchParams()
  const isEditMode = Boolean(recepcionId)
  const prefillOrdenCompraId = searchParams.get('orden_compra') || ''
  const permissions = usePermissions(['COMPRAS.CREAR', 'COMPRAS.EDITAR', 'COMPRAS.APROBAR'])

  const [loadingInitial, setLoadingInitial] = useState(true)
  const [saving, setSaving] = useState(false)
  const [recepcion, setRecepcion] = useState(null)

  const [ordenes, setOrdenes] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [productos, setProductos] = useState([])
  const [bodegas, setBodegas] = useState([])
  const [ocItems, setOcItems] = useState([])

  const [form, setForm] = useState({
    orden_compra: prefillOrdenCompraId,
    fecha: todayDate(),
    observaciones: '',
  })

  const [items, setItems] = useState([{ ...EMPTY_ITEM }])
  const { normalizeFieldValue, normalizeItemFields } = useNormalizedFormItems()

  // Dialogo de confirmacion
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmBodega, setConfirmBodega] = useState('')
  const [confirmando, setConfirmando] = useState(false)

  const loadInitialData = useCallback(async () => {
    setLoadingInitial(true)
    try {
      const [
        { data: ordenesData },
        { data: proveedoresData },
        { data: contactosData },
        productosData,
        { data: bodegasData },
      ] = await Promise.all([
        api.get('/ordenes-compra/', { suppressGlobalErrorToast: true }),
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
        getProductosCatalog(),
        api.get('/bodegas/', { suppressGlobalErrorToast: true }),
      ])

      setOrdenes(normalizeListResponse(ordenesData).filter((o) => o.estado !== 'CANCELADA' && o.estado !== 'BORRADOR'))
      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setProductos(productosData.filter((p) => String(p.tipo || '').toUpperCase() === 'PRODUCTO'))
      setBodegas(normalizeListResponse(bodegasData))

      if (isEditMode) {
        const [{ data: recData }, { data: recItemsData }] = await Promise.all([
          api.get(`/recepciones-compra/${recepcionId}/`, { suppressGlobalErrorToast: true }),
          api.get(`/recepciones-compra-items/?recepcion=${recepcionId}`, { suppressGlobalErrorToast: true }),
        ])

        setRecepcion(recData)
        setForm({
          orden_compra: recData.orden_compra ? String(recData.orden_compra) : '',
          fecha: recData.fecha || todayDate(),
          observaciones: recData.observaciones || '',
        })

        const loadedItems = normalizeListResponse(recItemsData)
        setItems(
          loadedItems.length > 0
            ? loadedItems.map((it) => ({
                _id: it.id,
                producto: String(it.producto || ''),
                orden_item: it.orden_item ? String(it.orden_item) : '',
                ...normalizeItemFields({
                  cantidad: it.cantidad || '1',
                  precio_unitario: it.precio_unitario || '0',
                }),
              }))
            : [{ ...EMPTY_ITEM }],
        )

        // Cargar items de la OC si corresponde
        if (recData.orden_compra) {
          const { data: ocItemsData } = await api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true })
          setOcItems(
            normalizeListResponse(ocItemsData).filter(
              (it) => String(it.orden_compra) === String(recData.orden_compra),
            ),
          )
        }
      } else {
        // Precargar items de OC si viene en la URL
        const prefillOcId = prefillOrdenCompraId
        if (prefillOcId) {
          const { data: ocItemsData } = await api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true })
          setOcItems(
            normalizeListResponse(ocItemsData).filter(
              (it) => String(it.orden_compra) === String(prefillOcId),
            ),
          )
        }
      }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los datos.' }))
    } finally {
      setLoadingInitial(false)
    }
  }, [isEditMode, prefillOrdenCompraId, recepcionId, normalizeItemFields])

  useEffect(() => {
    const id = setTimeout(() => { void loadInitialData() }, 0)
    return () => clearTimeout(id)
  }, [loadInitialData])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((c) => map.set(String(c.id), c))
    return map
  }, [contactos])

  const proveedorById = useMemo(() => {
    const map = new Map()
    proveedores.forEach((p) => map.set(String(p.id), p))
    return map
  }, [proveedores])

  const productoById = useMemo(() => {
    const map = new Map()
    productos.forEach((p) => map.set(String(p.id), p))
    return map
  }, [productos])

  const ordenOptions = useMemo(() =>
    ordenes.map((o) => {
      const prov = proveedorById.get(String(o.proveedor))
      const ctc = contactoById.get(String(prov?.contacto))
      return {
        value: String(o.id),
        label: `${o.numero || 'OC'} - ${ctc?.nombre || '-'} (${o.estado})`,
        keywords: `${o.numero || ''} ${ctc?.nombre || ''}`,
      }
    }),
    [ordenes, proveedorById, contactoById],
  )

  const productoOptions = useMemo(() =>
    productos.map((p) => ({
      value: String(p.id),
      label: p.nombre || `Producto ${p.id}`,
      keywords: `${p.sku || ''} ${p.tipo || ''}`,
    })),
    [productos],
  )

  const ocItemOptions = useMemo(() => {
    if (!ocItems.length) return []
    return ocItems.map((it) => {
      const prod = productoById.get(String(it.producto))
      return {
        value: String(it.id),
        label: `${prod?.nombre || 'Producto'} - cant: ${formatSmartNumber(it.cantidad, { maximumFractionDigits: 2 })} @ ${formatCurrencyCLP(it.precio_unitario || 0)}`,
      }
    })
  }, [ocItems, productoById])

  const handleFormChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleOrdenChange = useCallback(async (ordenId) => {
    setForm((prev) => ({ ...prev, orden_compra: ordenId }))
    setItems([{ ...EMPTY_ITEM }])
    if (!ordenId) {
      setOcItems([])
      return
    }
    try {
      const { data } = await api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true })
      setOcItems(normalizeListResponse(data).filter((it) => String(it.orden_compra) === String(ordenId)))
    } catch {
      setOcItems([])
    }
  }, [])

  const handleItemChange = (index, field, value) => {
    setItems((prev) => {
      const next = [...prev]
      const row = {
        ...next[index],
        [field]: normalizeFieldValue(field, value),
      }

      // Al seleccionar orden_item, auto-completar producto y precio
      if (field === 'orden_item' && value) {
        const ocItem = ocItems.find((it) => String(it.id) === String(value))
        if (ocItem) {
          row.producto = String(ocItem.producto || '')
          row.precio_unitario = toIntegerString(ocItem.precio_unitario || '0')
        }
      } else if (field === 'producto' && value && !row.orden_item) {
        const prod = productoById.get(String(value))
        if (prod) {
          row.precio_unitario = toIntegerString(prod.precio_referencia || 0)
        }
      }

      next[index] = row
      return next
    })
  }

  const addItem = () => setItems((prev) => [...prev, { ...EMPTY_ITEM }])

  const removeItem = (index) => {
    setItems((prev) => prev.filter((_, i) => i !== index))
  }

  const isReadOnly = recepcion?.estado === 'CONFIRMADA' || (isEditMode && !canEditarRecepcion(true, recepcion, permissions))

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!form.fecha) {
      toast.error('La fecha es obligatoria.')
      return
    }
    if (items.some((it) => !it.producto)) {
      toast.error('Todos los items deben tener producto.')
      return
    }
    if (items.some((it) => Number(it.cantidad) <= 0)) {
      toast.error('La cantidad debe ser mayor a cero.')
      return
    }

    setSaving(true)
    try {
      const headerPayload = {
        orden_compra: form.orden_compra || null,
        fecha: form.fecha,
        observaciones: form.observaciones.trim(),
      }

      let recId = recepcionId

      if (isEditMode) {
        await api.patch(`/recepciones-compra/${recepcionId}/`, headerPayload, { suppressGlobalErrorToast: true })

        // Eliminar items existentes y recrear
        const { data: existingItemsData } = await api.get(
          `/recepciones-compra-items/?recepcion=${recepcionId}`,
          { suppressGlobalErrorToast: true },
        )
        await Promise.all(
          normalizeListResponse(existingItemsData).map((it) =>
            api.delete(`/recepciones-compra-items/${it.id}/`, { suppressGlobalErrorToast: true }),
          ),
        )
      } else {
        const { data: newRec } = await api.post('/recepciones-compra/', headerPayload, {
          suppressGlobalErrorToast: true,
        })
        recId = newRec.id
      }

      await Promise.all(
        items.map((it) =>
          api.post('/recepciones-compra-items/', {
            recepcion: recId,
            producto: it.producto,
            orden_item: it.orden_item || null,
            cantidad: Number(it.cantidad),
            precio_unitario: Number(it.precio_unitario),
          }, { suppressGlobalErrorToast: true }),
        ),
      )

      toast.success(isEditMode ? 'Recepcion actualizada.' : 'Recepcion creada.')
      navigate('/compras/recepciones')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la recepcion.' }))
    } finally {
      setSaving(false)
    }
  }

  const handleConfirmar = async () => {
    setConfirmando(true)
    try {
      const payload = confirmBodega ? { bodega_id: confirmBodega } : {}
      await api.post(`/recepciones-compra/${recepcionId}/confirmar/`, payload, {
        suppressGlobalErrorToast: true,
      })
      toast.success('Recepcion confirmada. El inventario fue actualizado.')
      navigate('/compras/recepciones')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo confirmar la recepcion.' }))
    } finally {
      setConfirmando(false)
      setConfirmOpen(false)
    }
  }

  if (loadingInitial) {
    return <p className="text-sm text-muted-foreground">Cargando...</p>
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">
          {isReadOnly ? 'Detalle recepcion' : isEditMode ? 'Editar recepcion' : 'Nueva recepcion de compra'}
        </h2>
        {isEditMode && canConfirmarRecepcion(recepcion, permissions) ? (
          <Button variant="default" size="md" onClick={() => setConfirmOpen(true)}>
            Confirmar recepcion
          </Button>
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Datos de la recepcion */}
        <div className="rounded-md border border-border bg-card p-4 space-y-4">
          <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Datos de la recepcion</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Orden de compra (opcional)</label>
              <SearchableSelect
                value={form.orden_compra}
                onChange={(v) => { void handleOrdenChange(v) }}
                options={ordenOptions}
                ariaLabel="Orden de compra"
                placeholder="Seleccionar OC..."
                emptyText="No hay ordenes disponibles"
                disabled={isReadOnly}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Fecha</label>
              <input
                type="date"
                value={form.fecha}
                onChange={(e) => handleFormChange('fecha', e.target.value)}
                required
                disabled={isReadOnly}
                className="rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-60"
              />
            </div>
            <div className="flex flex-col gap-1 md:col-span-2">
              <label className="text-sm font-medium">Observaciones</label>
              <textarea
                value={form.observaciones}
                onChange={(e) => handleFormChange('observaciones', e.target.value)}
                rows={2}
                disabled={isReadOnly}
                className="rounded-md border border-input bg-background px-3 py-2 text-sm disabled:opacity-60"
                placeholder="Observaciones opcionales..."
              />
            </div>
          </div>
        </div>

        {/* Items */}
        <div className="rounded-md border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Items recepcionados</h3>
            {!isReadOnly ? (
              <Button type="button" variant="outline" size="sm" onClick={addItem}>
                + Agregar item
              </Button>
            ) : null}
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40">
                <tr>
                  {form.orden_compra ? (
                    <th className="px-3 py-2 text-left font-medium">Item OC</th>
                  ) : null}
                  <th className="px-3 py-2 text-left font-medium">Producto</th>
                  <th className="px-3 py-2 text-right font-medium">Cantidad</th>
                  <th className="px-3 py-2 text-right font-medium">Precio unit.</th>
                  {!isReadOnly ? <th className="px-3 py-2 text-right font-medium"></th> : null}
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => {
                  const prod = productoById.get(String(item.producto))
                  return (
                    <tr key={index} className="border-t border-border">
                      {form.orden_compra ? (
                        <td className="px-3 py-1 min-w-55">
                          {isReadOnly ? (
                            <span>{ocItemOptions.find((o) => o.value === item.orden_item)?.label || '-'}</span>
                          ) : (
                            <SearchableSelect
                              value={item.orden_item}
                              onChange={(v) => handleItemChange(index, 'orden_item', v)}
                              options={ocItemOptions}
                              ariaLabel="Item OC"
                              placeholder="Seleccionar item OC..."
                              emptyText="Sin items de OC"
                            />
                          )}
                        </td>
                      ) : null}
                      <td className="px-3 py-1 min-w-50">
                        {isReadOnly ? (
                          <span>{prod?.nombre || '-'}</span>
                        ) : (
                          <SearchableSelect
                            value={item.producto}
                            onChange={(v) => handleItemChange(index, 'producto', v)}
                            options={productoOptions}
                            ariaLabel="Producto"
                            placeholder="Seleccionar producto..."
                            emptyText="Sin productos"
                          />
                        )}
                      </td>
                      <td className="px-3 py-1 text-right">
                        {isReadOnly ? (
                          <span>{formatSmartNumber(item.cantidad, { maximumFractionDigits: 2 })}</span>
                        ) : (
                          <input
                            type="text"
                            inputMode="decimal"
                            value={item.cantidad}
                            onChange={(e) => handleItemChange(index, 'cantidad', e.target.value)}
                            className="w-24 rounded-md border border-input bg-background px-2 py-1 text-sm text-right"
                          />
                        )}
                      </td>
                      <td className="px-3 py-1 text-right">
                        {isReadOnly ? (
                          <span>{formatCurrencyCLP(item.precio_unitario || 0)}</span>
                        ) : (
                          <input
                            type="text"
                            inputMode="numeric"
                            value={item.precio_unitario}
                            onChange={(e) => handleItemChange(index, 'precio_unitario', e.target.value)}
                            className="w-28 rounded-md border border-input bg-background px-2 py-1 text-sm text-right"
                          />
                        )}
                      </td>
                      {!isReadOnly ? (
                        <td className="px-3 py-1 text-right">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="border-destructive/40 text-destructive hover:bg-destructive/10 h-7 px-2 text-xs"
                            onClick={() => removeItem(index)}
                            disabled={items.length === 1}
                          >
                            Quitar
                          </Button>
                        </td>
                      ) : null}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {!isReadOnly && (canCrearRecepcion(isEditMode, permissions) || canEditarRecepcion(isEditMode, recepcion, permissions)) ? (
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={() => navigate('/compras/recepciones')}
              disabled={saving}
            >
              Cancelar
            </Button>
            <Button type="submit" variant="default" size="md" disabled={saving}>
              {saving ? 'Guardando...' : isEditMode ? 'Guardar cambios' : 'Crear recepcion'}
            </Button>
          </div>
        ) : (
          <div className="flex justify-end">
            <Button variant="outline" size="md" onClick={() => navigate('/compras/recepciones')}>
              Volver
            </Button>
          </div>
        )}
      </form>

      {/* Dialogo de confirmacion */}
      {confirmOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-background p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold">Confirmar recepcion</h3>
            <p className="text-sm text-muted-foreground">
              Esta accion registrara los movimientos de inventario y no se puede deshacer.
              Asegurese de que los items y cantidades sean correctos antes de continuar.
            </p>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium">Bodega destino (opcional)</label>
              <select
                value={confirmBodega}
                onChange={(e) => setConfirmBodega(e.target.value)}
                className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Bodega por defecto</option>
                {bodegas.map((b) => (
                  <option key={b.id} value={b.id}>{b.nombre}</option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="md" onClick={() => setConfirmOpen(false)} disabled={confirmando}>
                Cancelar
              </Button>
              <Button variant="default" size="md" onClick={handleConfirmar} disabled={confirmando}>
                {confirmando ? 'Confirmando...' : 'Confirmar'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export default ComprasRecepcionesCreatePage
