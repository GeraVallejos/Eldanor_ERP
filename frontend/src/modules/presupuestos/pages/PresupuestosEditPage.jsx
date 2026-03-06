import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
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

function createEmptyItem(uiKey, expanded = false) {
  return {
    uiKey,
    expanded,
    id: null,
    tipo: 'PRODUCTO',
    producto: '',
    producto_search: '',
    descripcion: '',
    cantidad: '1',
    precio_unitario: '0',
    descuento: '0',
    impuesto: '',
  }
}

function firstErrorMessage(value) {
  if (typeof value === 'string') {
    return value
  }

  if (Array.isArray(value) && typeof value[0] === 'string') {
    return value[0]
  }

  return null
}

function normalizeText(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

function formatMoney(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }

  return Math.round(num).toLocaleString('es-CL')
}

function toIntegerString(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }

  return String(Math.round(num))
}

function PresupuestosEditPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const nextItemKeyRef = useRef(2)
  const [status, setStatus] = useState('idle')
  const [loading, setLoading] = useState(true)
  const [presupuestoNumero, setPresupuestoNumero] = useState('')
  const [clientes, setClientes] = useState([])
  const [contactos, setContactos] = useState([])
  const [productos, setProductos] = useState([])
  const [impuestos, setImpuestos] = useState([])
  const [items, setItems] = useState([createEmptyItem('new-1')])
  const [initialItemIds, setInitialItemIds] = useState([])
  const [clienteSearch, setClienteSearch] = useState('')
  const [clienteDropdownOpen, setClienteDropdownOpen] = useState(false)
  const [clienteCursorIndex, setClienteCursorIndex] = useState(-1)
  const [fieldErrors, setFieldErrors] = useState({
    cliente: '',
    fecha: '',
    fecha_vencimiento: '',
    descuento: '',
    observaciones: '',
    items: '',
  })
  const [itemErrors, setItemErrors] = useState([{}])
  const [openProductoPickerIndex, setOpenProductoPickerIndex] = useState(null)
  const [productoPickerCursor, setProductoPickerCursor] = useState({
    itemIndex: null,
    optionIndex: -1,
  })
  const [form, setForm] = useState({
    cliente: '',
    fecha: '',
    fecha_vencimiento: '',
    descuento: 0,
    observaciones: '',
  })

  const getNextItemKey = () => {
    const key = `new-${nextItemKeyRef.current}`
    nextItemKeyRef.current += 1
    return key
  }

  useEffect(() => {
    if (!id) {
      toast.error('No se encontro el presupuesto a editar.')
      navigate('/presupuestos')
      return
    }

    const timeoutId = setTimeout(() => {
      void (async () => {
        setLoading(true)

        try {
          const [
            { data: presupuestoData },
            { data: itemsData },
            { data: clientesData },
            { data: contactosData },
            { data: productosData },
            { data: impuestosData },
          ] = await Promise.all([
            api.get(`/presupuestos/${id}/`, { suppressGlobalErrorToast: true }),
            api.get('/presupuesto-items/', { suppressGlobalErrorToast: true }),
            api.get('/clientes/', { suppressGlobalErrorToast: true }),
            api.get('/contactos/', { suppressGlobalErrorToast: true }),
            api.get('/productos/', { suppressGlobalErrorToast: true }),
            api.get('/impuestos/', { suppressGlobalErrorToast: true }),
          ])

          const clientesList = normalizeListResponse(clientesData)
          const contactosList = normalizeListResponse(contactosData)
          const productosList = normalizeListResponse(productosData)
          const impuestosList = normalizeListResponse(impuestosData)
          const allItems = normalizeListResponse(itemsData)
          const scopedItems = allItems.filter((item) => String(item.presupuesto) === String(id))

          const contactoMap = new Map()
          contactosList.forEach((contacto) => {
            contactoMap.set(String(contacto.id), contacto)
          })

          const productMap = new Map()
          productosList.forEach((producto) => {
            productMap.set(String(producto.id), producto)
          })

          const clienteSeleccionado = clientesList.find(
            (cliente) => String(cliente.id) === String(presupuestoData.cliente),
          )
          const contactoSeleccionado = contactoMap.get(String(clienteSeleccionado?.contacto || ''))

          setClientes(clientesList)
          setContactos(contactosList)
          setProductos(productosList)
          setImpuestos(impuestosList)
          setPresupuestoNumero(presupuestoData.numero || '')
          setForm({
            cliente: String(presupuestoData.cliente || ''),
            fecha: presupuestoData.fecha || '',
            fecha_vencimiento: presupuestoData.fecha_vencimiento || '',
            descuento: presupuestoData.descuento ?? 0,
            observaciones: presupuestoData.observaciones || '',
          })
          setClienteSearch(contactoSeleccionado?.nombre || '')

          const mappedItems = scopedItems.map((item, index) => {
            const producto = item.producto ? productMap.get(String(item.producto)) : null
            const tipo = producto ? String(producto.tipo || 'PRODUCTO').toUpperCase() : 'SERVICIO'

            return {
              uiKey: String(item.id || `existing-${index}`),
              expanded: false,
              id: item.id,
              tipo,
              producto: item.producto ? String(item.producto) : '',
              producto_search: producto?.nombre || '',
              descripcion: item.descripcion || '',
              cantidad: String(item.cantidad ?? '1'),
              precio_unitario: toIntegerString(item.precio_unitario ?? '0'),
              descuento: String(item.descuento ?? '0'),
              impuesto: item.impuesto ? String(item.impuesto) : '',
            }
          })

          const loadedItems = mappedItems.length > 0 ? mappedItems : [createEmptyItem(getNextItemKey(), false)]
          setItems(loadedItems)
          setItemErrors(loadedItems.map(() => ({})))
          setInitialItemIds(mappedItems.map((item) => item.id).filter(Boolean))
        } catch (error) {
          toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el presupuesto.' }))
          navigate('/presupuestos')
        } finally {
          setLoading(false)
        }
      })()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [id, navigate])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => {
      map.set(String(contacto.id), contacto)
    })
    return map
  }, [contactos])

  const clientOptions = useMemo(() => {
    return clientes.map((cliente) => {
      const contacto = contactoById.get(String(cliente.contacto))
      return {
        value: String(cliente.id),
        label: contacto?.nombre || `Cliente #${cliente.id}`,
        rut: contacto?.rut || '',
        email: contacto?.email || '',
      }
    })
  }, [clientes, contactoById])

  const filteredClientOptions = useMemo(() => {
    const query = normalizeText(clienteSearch)
    if (!query) {
      return clientOptions
    }

    return clientOptions.filter((option) => {
      return (
        normalizeText(option.label).includes(query) ||
        normalizeText(option.rut).includes(query) ||
        normalizeText(option.email).includes(query)
      )
    })
  }, [clientOptions, clienteSearch])

  const productosOptions = useMemo(
    () => productos.filter((producto) => String(producto.tipo || '').toUpperCase() === 'PRODUCTO'),
    [productos],
  )

  const serviciosOptions = useMemo(
    () => productos.filter((producto) => String(producto.tipo || '').toUpperCase() === 'SERVICIO'),
    [productos],
  )

  const productoById = useMemo(() => {
    const map = new Map()
    productos.forEach((producto) => {
      map.set(String(producto.id), producto)
    })
    return map
  }, [productos])

  const impuestoById = useMemo(() => {
    const map = new Map()
    impuestos.forEach((impuesto) => {
      map.set(String(impuesto.id), impuesto)
    })
    return map
  }, [impuestos])

  const summary = useMemo(() => {
    const itemSubtotal = items.reduce((acc, item) => {
      const cantidad = Number(item.cantidad)
      const precio = Number(item.precio_unitario)
      const descPct = Number(item.descuento || 0)

      const safeCantidad = Number.isFinite(cantidad) && cantidad > 0 ? cantidad : 0
      const safePrecio = Number.isFinite(precio) && precio >= 0 ? precio : 0
      const safeDescPct = Number.isFinite(descPct) && descPct >= 0 ? Math.min(descPct, 100) : 0

      const bruto = safeCantidad * safePrecio
      const descuentoItem = bruto * (safeDescPct / 100)
      return acc + Math.max(bruto - descuentoItem, 0)
    }, 0)

    const impuestoEstimado = items.reduce((acc, item) => {
      const cantidad = Number(item.cantidad)
      const precio = Number(item.precio_unitario)
      const descPct = Number(item.descuento || 0)
      const impuesto = item.impuesto ? impuestoById.get(String(item.impuesto)) : null
      const tasa = Number(impuesto?.porcentaje || 0)

      const safeCantidad = Number.isFinite(cantidad) && cantidad > 0 ? cantidad : 0
      const safePrecio = Number.isFinite(precio) && precio >= 0 ? precio : 0
      const safeDescPct = Number.isFinite(descPct) && descPct >= 0 ? Math.min(descPct, 100) : 0
      const safeTasa = Number.isFinite(tasa) && tasa >= 0 ? tasa : 0

      const bruto = safeCantidad * safePrecio
      const descuentoItem = bruto * (safeDescPct / 100)
      const neto = Math.max(bruto - descuentoItem, 0)
      return acc + neto * (safeTasa / 100)
    }, 0)

    const descuentoGlobal = Number(form.descuento)
    const safeDescuentoGlobal =
      Number.isFinite(descuentoGlobal) && descuentoGlobal > 0 ? descuentoGlobal : 0

    const totalEstimado = Math.max(itemSubtotal - safeDescuentoGlobal, 0) + impuestoEstimado

    return {
      itemSubtotal,
      descuentoGlobal: safeDescuentoGlobal,
      impuestoEstimado,
      totalEstimado,
    }
  }, [form.descuento, impuestoById, items])

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))

    if (key === 'cliente') {
      const selected = clientOptions.find((option) => option.value === String(value))
      if (selected) {
        setClienteSearch(selected.label)
      }
    }

    setFieldErrors((prev) => ({ ...prev, [key]: '' }))
  }

  const selectClienteOption = (option) => {
    setForm((prev) => ({ ...prev, cliente: option.value }))
    setClienteSearch(option.label)
    setClienteDropdownOpen(false)
    setClienteCursorIndex(-1)
    setFieldErrors((prev) => ({ ...prev, cliente: '' }))
  }

  const handleClienteSearchChange = (value) => {
    setClienteSearch(value)
    setClienteDropdownOpen(true)
    setClienteCursorIndex(-1)

    const exactMatch = clientOptions.find(
      (option) =>
        normalizeText(option.label) === normalizeText(value) ||
        normalizeText(option.rut) === normalizeText(value) ||
        normalizeText(option.email) === normalizeText(value),
    )

    if (exactMatch) {
      setForm((prev) => ({ ...prev, cliente: exactMatch.value }))
      setFieldErrors((prev) => ({ ...prev, cliente: '' }))
      return
    }

    setForm((prev) => ({ ...prev, cliente: '' }))
  }

  const clearClienteSearch = () => {
    setClienteSearch('')
    setForm((prev) => ({ ...prev, cliente: '' }))
    setClienteDropdownOpen(true)
    setClienteCursorIndex(-1)
    setFieldErrors((prev) => ({ ...prev, cliente: '' }))
  }

  const handleClienteSearchKeyDown = (event) => {
    const options = filteredClientOptions

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (options.length === 0) {
        return
      }

      setClienteDropdownOpen(true)
      setClienteCursorIndex((prev) => Math.min(prev + 1, options.length - 1))
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (options.length === 0) {
        return
      }

      setClienteDropdownOpen(true)
      setClienteCursorIndex((prev) => Math.max(prev - 1, 0))
      return
    }

    if (event.key === 'Enter') {
      if (clienteDropdownOpen && options.length > 0) {
        event.preventDefault()
        const option = clienteCursorIndex >= 0 ? options[clienteCursorIndex] : options[0]
        if (option) {
          selectClienteOption(option)
        }
      }
      return
    }

    if (event.key === 'Escape') {
      setClienteDropdownOpen(false)
      setClienteCursorIndex(-1)
    }
  }

  const updateItemField = (index, key, value) => {
    setItems((prev) => {
      const next = [...prev]
      const normalizedValue = key === 'precio_unitario' ? toIntegerString(value) : value
      const current = { ...next[index], [key]: normalizedValue }

      if (key === 'tipo') {
        current.producto = ''
        current.producto_search = ''
        current.impuesto = ''
      }

      if (key === 'producto') {
        const selectedProducto = productoById.get(String(value))
        if (selectedProducto) {
          current.producto_search = selectedProducto.nombre || ''
          current.descripcion = selectedProducto.nombre || current.descripcion || ''
          current.precio_unitario = toIntegerString(selectedProducto.precio_referencia ?? 0)
          current.impuesto = selectedProducto.impuesto ? String(selectedProducto.impuesto) : ''
        }
      }

      next[index] = current
      return next
    })

    setItemErrors((prev) => {
      const next = [...prev]
      next[index] = { ...(next[index] || {}), [key]: '' }
      return next
    })

    if (fieldErrors.items) {
      setFieldErrors((prev) => ({ ...prev, items: '' }))
    }
  }

  const addItem = () => {
    setItems((prev) => [...prev, createEmptyItem(getNextItemKey(), false)])
    setItemErrors((prev) => [...prev, {}])
    if (fieldErrors.items) {
      setFieldErrors((prev) => ({ ...prev, items: '' }))
    }
  }

  const removeItem = (index) => {
    if (items.length <= 1) {
      setFieldErrors((prev) => ({ ...prev, items: 'Debes agregar al menos un item.' }))
      return
    }

    setItems((prev) => prev.filter((_, idx) => idx !== index))
    setItemErrors((prev) => prev.filter((_, idx) => idx !== index))

    if (openProductoPickerIndex === index) {
      setOpenProductoPickerIndex(null)
      setProductoPickerCursor({ itemIndex: null, optionIndex: -1 })
    } else if (typeof openProductoPickerIndex === 'number' && openProductoPickerIndex > index) {
      setOpenProductoPickerIndex((prev) => (typeof prev === 'number' ? prev - 1 : null))
      setProductoPickerCursor((prev) => {
        if (typeof prev.itemIndex !== 'number') {
          return prev
        }

        return prev.itemIndex > index
          ? { ...prev, itemIndex: prev.itemIndex - 1 }
          : prev
      })
    }
  }

  const toggleItemExpanded = (index) => {
    setItems((prev) => {
      const next = [...prev]
      next[index] = { ...next[index], expanded: !next[index].expanded }
      return next
    })
  }

  const setAllItemsExpanded = (expanded) => {
    setItems((prev) => prev.map((item) => ({ ...item, expanded })))
  }

  const formatQuantityPreview = (value) => {
    const num = Number(value)
    if (!Number.isFinite(num)) {
      return '0'
    }

    return num.toLocaleString('es-CL', {
      maximumFractionDigits: 2,
    })
  }

  const getItemPreview = (item) => {
    const description = String(item.descripcion || '').trim()
    const cantidad = Number(item.cantidad)
    const precio = Number(item.precio_unitario)

    const cantidadText = Number.isFinite(cantidad) ? formatQuantityPreview(cantidad) : '0'
    const precioText = Number.isFinite(precio) ? formatMoney(precio) : '0'

    return `${description || 'Sin descripcion'} | Cant: ${cantidadText} | Precio: ${precioText}`
  }

  const getFilteredProductosForItem = (item) => {
    const baseOptions =
      String(item.tipo || 'PRODUCTO').toUpperCase() === 'SERVICIO' ? serviciosOptions : productosOptions

    const query = normalizeText(item.producto_search)
    if (!query) {
      return baseOptions
    }

    return baseOptions.filter((producto) => normalizeText(producto.nombre).includes(query))
  }

  const selectProductoForItem = (index, producto) => {
    setItems((prev) => {
      const next = [...prev]
      const current = { ...next[index] }
      current.producto = String(producto.id)
      current.producto_search = producto.nombre || ''
      current.descripcion = producto.nombre || current.descripcion || ''
      current.precio_unitario = toIntegerString(producto.precio_referencia ?? 0)
      current.impuesto = producto.impuesto ? String(producto.impuesto) : ''
      next[index] = current
      return next
    })

    setItemErrors((prev) => {
      const next = [...prev]
      next[index] = { ...(next[index] || {}), producto: '' }
      return next
    })

    setOpenProductoPickerIndex(null)
    setProductoPickerCursor({ itemIndex: null, optionIndex: -1 })
  }

  const clearProductoSearchForItem = (index) => {
    setItems((prev) => {
      const next = [...prev]
      const current = { ...next[index] }
      current.producto = ''
      current.producto_search = ''
      next[index] = current
      return next
    })

    setItemErrors((prev) => {
      const next = [...prev]
      next[index] = { ...(next[index] || {}), producto: '' }
      return next
    })
  }

  const handleProductoSearchChange = (index, value) => {
    setItems((prev) => {
      const next = [...prev]
      const current = { ...next[index] }
      current.producto_search = value

      const options =
        String(current.tipo || 'PRODUCTO').toUpperCase() === 'SERVICIO' ? serviciosOptions : productosOptions

      const exactMatch = options.find((producto) => normalizeText(producto.nombre) === normalizeText(value))

      if (exactMatch) {
        current.producto = String(exactMatch.id)
      } else {
        current.producto = ''
      }

      next[index] = current
      return next
    })

    setItemErrors((prev) => {
      const next = [...prev]
      next[index] = { ...(next[index] || {}), producto: '' }
      return next
    })

    setProductoPickerCursor({ itemIndex: index, optionIndex: -1 })
  }

  const handleProductoSearchKeyDown = (index, event) => {
    const options = getFilteredProductosForItem(items[index])

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (options.length === 0) {
        return
      }

      setOpenProductoPickerIndex(index)
      setProductoPickerCursor((prev) => {
        if (prev.itemIndex !== index) {
          return { itemIndex: index, optionIndex: 0 }
        }
        return {
          itemIndex: index,
          optionIndex: Math.min(prev.optionIndex + 1, options.length - 1),
        }
      })
      return
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (options.length === 0) {
        return
      }

      setOpenProductoPickerIndex(index)
      setProductoPickerCursor((prev) => {
        if (prev.itemIndex !== index || prev.optionIndex < 0) {
          return { itemIndex: index, optionIndex: 0 }
        }
        return {
          itemIndex: index,
          optionIndex: Math.max(prev.optionIndex - 1, 0),
        }
      })
      return
    }

    if (event.key === 'Enter') {
      if (openProductoPickerIndex === index && options.length > 0) {
        event.preventDefault()
        const targetOption =
          productoPickerCursor.itemIndex === index && productoPickerCursor.optionIndex >= 0
            ? options[productoPickerCursor.optionIndex]
            : options[0]
        if (targetOption) {
          selectProductoForItem(index, targetOption)
        }
      }
      return
    }

    if (event.key === 'Escape') {
      setOpenProductoPickerIndex(null)
      setProductoPickerCursor({ itemIndex: null, optionIndex: -1 })
    }
  }

  const validateInline = () => {
    const nextFieldErrors = {
      cliente: '',
      fecha: '',
      fecha_vencimiento: '',
      descuento: '',
      observaciones: '',
      items: '',
    }

    if (!form.fecha) {
      nextFieldErrors.fecha = 'La fecha es obligatoria.'
    }

    const descuento = Number(form.descuento)
    if (Number.isNaN(descuento) || descuento < 0) {
      nextFieldErrors.descuento = 'El descuento no puede ser negativo.'
    }

    if (items.length === 0) {
      nextFieldErrors.items = 'Debes agregar al menos un item.'
    }

    const nextItemErrors = items.map((item) => {
      const errors = {}

      const itemType = String(item.tipo || 'PRODUCTO').toUpperCase()

      if (itemType === 'PRODUCTO' && !item.producto) {
        errors.producto = 'Debes seleccionar un producto.'
      }

      if (!String(item.descripcion || '').trim()) {
        errors.descripcion =
          itemType === 'SERVICIO'
            ? 'La descripcion del servicio es obligatoria.'
            : 'La descripcion es obligatoria.'
      }

      const cantidad = Number(item.cantidad)
      if (Number.isNaN(cantidad) || cantidad <= 0) {
        errors.cantidad = 'La cantidad debe ser mayor a 0.'
      }

      const precioUnitario = Number(item.precio_unitario)
      if (Number.isNaN(precioUnitario) || precioUnitario < 0) {
        errors.precio_unitario = 'El precio unitario no puede ser negativo.'
      }

      const descuentoItem = Number(item.descuento || 0)
      if (Number.isNaN(descuentoItem) || descuentoItem < 0 || descuentoItem > 100) {
        errors.descuento = 'El descuento del item debe estar entre 0 y 100.'
      }

      return errors
    })

    setFieldErrors(nextFieldErrors)
    setItemErrors(nextItemErrors)

    const hasFieldErrors = Object.values(nextFieldErrors).some(Boolean)
    const hasItemErrors = nextItemErrors.some((errors) => Object.keys(errors).length > 0)
    return !hasFieldErrors && !hasItemErrors
  }

  const resolveClienteId = () => {
    if (form.cliente) {
      const selected = clientOptions.find((option) => option.value === String(form.cliente))
      if (selected) {
        return selected.value
      }
    }

    const query = normalizeText(clienteSearch)
    if (!query) {
      return null
    }

    const exactMatch = clientOptions.find((option) => normalizeText(option.label) === query)
    if (exactMatch) {
      return exactMatch.value
    }

    const exactRutOrEmail = clientOptions.find(
      (option) => normalizeText(option.rut) === query || normalizeText(option.email) === query,
    )
    if (exactRutOrEmail) {
      return exactRutOrEmail.value
    }

    const startsWithMatch = filteredClientOptions.find((option) =>
      normalizeText(option.label).startsWith(query),
    )
    if (startsWithMatch) {
      return startsWithMatch.value
    }

    if (filteredClientOptions.length > 0) {
      return filteredClientOptions[0].value
    }

    return null
  }

  const applyBackendFieldErrors = (data) => {
    if (!data || typeof data !== 'object') {
      return false
    }

    let applied = false
    const nextFieldErrors = { ...fieldErrors }

    ;['cliente', 'fecha', 'fecha_vencimiento', 'descuento', 'observaciones'].forEach((key) => {
      const msg = firstErrorMessage(data[key])
      if (msg) {
        nextFieldErrors[key] = msg
        applied = true
      }
    })

    const nonField = firstErrorMessage(data.non_field_errors)
    if (nonField) {
      nextFieldErrors.items = nonField
      applied = true
    }

    if (applied) {
      setFieldErrors(nextFieldErrors)
    }

    return applied
  }

  const applyBackendItemErrors = (index, data) => {
    if (!data || typeof data !== 'object' || index < 0) {
      return false
    }

    const nextItemErrors = [...itemErrors]
    const rowErrors = { ...(nextItemErrors[index] || {}) }
    let applied = false

    ;['producto', 'descripcion', 'cantidad', 'precio_unitario', 'descuento', 'impuesto'].forEach((key) => {
      const msg = firstErrorMessage(data[key])
      if (msg) {
        rowErrors[key] = msg
        applied = true
      }
    })

    const rowNonField = firstErrorMessage(data.non_field_errors)
    if (rowNonField) {
      rowErrors.descripcion = rowErrors.descripcion || rowNonField
      applied = true
    }

    if (applied) {
      nextItemErrors[index] = rowErrors
      setItemErrors(nextItemErrors)
    }

    return applied
  }

  const onSubmit = async (event) => {
    event.preventDefault()

    if (!id) {
      return
    }

    if (!validateInline()) {
      return
    }

    const clienteId = resolveClienteId()
    if (!clienteId) {
      setFieldErrors((prev) => ({
        ...prev,
        cliente: 'Debes seleccionar un cliente valido desde la lista.',
      }))
      setClienteDropdownOpen(true)
      return
    }

    setStatus('loading')
    setFieldErrors({
      cliente: '',
      fecha: '',
      fecha_vencimiento: '',
      descuento: '',
      observaciones: '',
      items: '',
    })
    setItemErrors((prev) => prev.map(() => ({})))

    let updatingItemIndex = -1

    try {
      await api.patch(
        `/presupuestos/${id}/`,
        {
          cliente: String(clienteId),
          fecha: form.fecha,
          fecha_vencimiento: form.fecha_vencimiento || null,
          descuento: Number(form.descuento) || 0,
          observaciones: form.observaciones || '',
        },
        { suppressGlobalErrorToast: true },
      )

      const currentIds = items.map((item) => item.id).filter(Boolean)
      const idsToDelete = initialItemIds.filter((itemId) => !currentIds.includes(itemId))

      for (const itemId of idsToDelete) {
        await api.delete(`/presupuesto-items/${itemId}/`, { suppressGlobalErrorToast: true })
      }

      for (let index = 0; index < items.length; index += 1) {
        updatingItemIndex = index
        const item = items[index]
        const payload = {
          presupuesto: id,
          producto: item.producto || null,
          descripcion: String(item.descripcion || '').trim(),
          cantidad: Number(item.cantidad),
          precio_unitario: Number(item.precio_unitario),
          descuento: Number(item.descuento || 0),
          impuesto: item.impuesto || null,
        }

        if (item.id) {
          await api.patch(`/presupuesto-items/${item.id}/`, payload, {
            suppressGlobalErrorToast: true,
          })
        } else {
          const { data: createdItem } = await api.post('/presupuesto-items/', payload, {
            suppressGlobalErrorToast: true,
          })
          if (createdItem?.id) {
            items[index].id = createdItem.id
          }
        }
      }

      toast.success('Presupuesto actualizado correctamente.')
      navigate('/presupuestos')
    } catch (error) {
      const data = error?.response?.data
      const appliedTopErrors = applyBackendFieldErrors(data)
      const appliedItemErrors = applyBackendItemErrors(updatingItemIndex, data)

      if (!appliedTopErrors && !appliedItemErrors) {
        toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el presupuesto.' }))
      }
    } finally {
      setStatus('idle')
    }
  }

  if (loading) {
    return (
      <section className="space-y-4">
        <p className="text-sm text-muted-foreground">Cargando presupuesto...</p>
      </section>
    )
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Editar presupuesto {presupuestoNumero ? `Nro ${presupuestoNumero}` : ''}</h2>
          <p className="text-sm text-muted-foreground">Edita encabezado e items en una pagina completa.</p>
        </div>
        <Link
          to="/presupuestos"
          className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'w-full sm:w-auto')}
        >
          Volver al listado
        </Link>
      </div>

      <form className="rounded-md border border-border bg-card p-4" onSubmit={onSubmit}>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm md:col-span-2">
            Cliente
            <div className="relative mt-1">
              <input
                type="text"
                className={[
                  'w-full rounded-md border bg-background px-3 py-2 pr-9 text-sm',
                  fieldErrors.cliente ? 'border-destructive' : 'border-input',
                ].join(' ')}
                value={clienteSearch}
                onChange={(event) => handleClienteSearchChange(event.target.value)}
                onFocus={() => {
                  setClienteDropdownOpen(true)
                  setClienteCursorIndex(-1)
                }}
                onKeyDown={handleClienteSearchKeyDown}
                onBlur={() => {
                  setTimeout(() => {
                    setClienteDropdownOpen(false)
                    setClienteCursorIndex(-1)
                  }, 120)
                }}
                placeholder="Buscar y seleccionar cliente..."
                autoComplete="off"
              />

              {clienteSearch ? (
                <button
                  type="button"
                  onMouseDown={(event) => {
                    event.preventDefault()
                    clearClienteSearch()
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Limpiar busqueda de cliente"
                >
                  x
                </button>
              ) : null}

              {clienteDropdownOpen && (
                <div className="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-md border border-border bg-popover p-1 shadow-lg">
                  {filteredClientOptions.length === 0 ? (
                    <p className="px-2 py-2 text-xs text-muted-foreground">
                      No hay clientes para "{clienteSearch}".
                    </p>
                  ) : (
                    filteredClientOptions.slice(0, 30).map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        onMouseDown={(event) => {
                          event.preventDefault()
                          selectClienteOption(option)
                        }}
                        onMouseEnter={() => {
                          const optionIndex = filteredClientOptions.findIndex((opt) => opt.value === option.value)
                          setClienteCursorIndex(optionIndex)
                        }}
                        className={[
                          'flex w-full items-center justify-between rounded px-2 py-2 text-left text-sm hover:bg-muted',
                          clienteCursorIndex >= 0 && filteredClientOptions[clienteCursorIndex]?.value === option.value
                            ? 'bg-muted'
                            : '',
                        ].join(' ')}
                      >
                        <span className="truncate">{option.label}</span>
                        {option.rut ? (
                          <span className="ml-2 shrink-0 text-xs text-muted-foreground">{option.rut}</span>
                        ) : null}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            <span className="mt-1 block text-xs text-muted-foreground">
              Escribe para buscar y selecciona el cliente en el mismo campo.
            </span>
            {fieldErrors.cliente && (
              <span className="mt-1 block text-xs text-destructive">{fieldErrors.cliente}</span>
            )}
          </label>

          <label className="text-sm">
            Fecha
            <input
              type="date"
              className={[
                'mt-1 w-full rounded-md border bg-background px-3 py-2',
                fieldErrors.fecha ? 'border-destructive' : 'border-input',
              ].join(' ')}
              value={form.fecha}
              onChange={(event) => updateField('fecha', event.target.value)}
              required
            />
            {fieldErrors.fecha && (
              <span className="mt-1 block text-xs text-destructive">{fieldErrors.fecha}</span>
            )}
          </label>

          <label className="text-sm">
            Fecha vencimiento
            <input
              type="date"
              className={[
                'mt-1 w-full rounded-md border bg-background px-3 py-2',
                fieldErrors.fecha_vencimiento ? 'border-destructive' : 'border-input',
              ].join(' ')}
              value={form.fecha_vencimiento}
              onChange={(event) => updateField('fecha_vencimiento', event.target.value)}
            />
            {fieldErrors.fecha_vencimiento && (
              <span className="mt-1 block text-xs text-destructive">{fieldErrors.fecha_vencimiento}</span>
            )}
          </label>

          <label className="text-sm">
            Descuento
            <input
              type="number"
              min="0"
              step="1"
              className={[
                'mt-1 w-full rounded-md border bg-background px-3 py-2',
                fieldErrors.descuento ? 'border-destructive' : 'border-input',
              ].join(' ')}
              value={form.descuento}
              onChange={(event) => updateField('descuento', event.target.value)}
            />
            {fieldErrors.descuento && (
              <span className="mt-1 block text-xs text-destructive">{fieldErrors.descuento}</span>
            )}
          </label>

          <label className="text-sm md:col-span-2">
            Observaciones
            <textarea
              rows={3}
              className={[
                'mt-1 w-full rounded-md border bg-background px-3 py-2',
                fieldErrors.observaciones ? 'border-destructive' : 'border-input',
              ].join(' ')}
              value={form.observaciones}
              onChange={(event) => updateField('observaciones', event.target.value)}
            />
            {fieldErrors.observaciones && (
              <span className="mt-1 block text-xs text-destructive">{fieldErrors.observaciones}</span>
            )}
          </label>
        </div>

        <div className="mt-5 rounded-lg border border-border p-3">
          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-sm font-semibold">Items del presupuesto</h3>
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setAllItemsExpanded(true)}>
                Expandir todo
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => setAllItemsExpanded(false)}>
                Contraer todo
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={addItem}>
                Agregar item
              </Button>
            </div>
          </div>

          {fieldErrors.items && <p className="mb-2 text-xs text-destructive">{fieldErrors.items}</p>}

          <div className="space-y-3">
            {items.map((item, index) => (
              <div key={item.uiKey || item.id || `item-${index}`} className="rounded-md border border-border p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground">Item {index + 1}</p>
                    {!item.expanded && (
                      <p className="max-w-208 truncate text-xs text-muted-foreground">{getItemPreview(item)}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => toggleItemExpanded(index)}
                      className="h-7 px-2 text-xs"
                    >
                      {item.expanded ? 'Contraer' : 'Expandir'}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeItem(index)}
                      className="h-7 px-2 text-xs"
                    >
                      Quitar
                    </Button>
                  </div>
                </div>

                {item.expanded && <div className="grid gap-3 md:grid-cols-2">
                  <label className="text-sm">
                    Tipo item
                    <select
                      className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                      value={item.tipo || 'PRODUCTO'}
                      onChange={(event) => updateItemField(index, 'tipo', event.target.value)}
                    >
                      <option value="PRODUCTO">Producto</option>
                      <option value="SERVICIO">Servicio</option>
                    </select>
                  </label>

                  <label className="text-sm">
                    {String(item.tipo || 'PRODUCTO').toUpperCase() === 'SERVICIO'
                      ? 'Servicio existente (opcional)'
                      : 'Producto'}
                    <div className="relative mt-1">
                      <input
                        type="text"
                        className={[
                          'w-full rounded-md border bg-background px-3 py-2 pr-9 text-sm',
                          itemErrors[index]?.producto ? 'border-destructive' : 'border-input',
                        ].join(' ')}
                        value={item.producto_search || ''}
                        onChange={(event) => handleProductoSearchChange(index, event.target.value)}
                        onFocus={() => {
                          setOpenProductoPickerIndex(index)
                          setProductoPickerCursor({ itemIndex: index, optionIndex: -1 })
                        }}
                        onKeyDown={(event) => handleProductoSearchKeyDown(index, event)}
                        onBlur={() => {
                          setTimeout(() => {
                            setOpenProductoPickerIndex((prev) => {
                              if (prev === index) {
                                setProductoPickerCursor({ itemIndex: null, optionIndex: -1 })
                                return null
                              }
                              return prev
                            })
                          }, 120)
                        }}
                        placeholder={
                          String(item.tipo || 'PRODUCTO').toUpperCase() === 'SERVICIO'
                            ? 'Buscar servicio (o dejar vacio para manual)...'
                            : 'Buscar producto...'
                        }
                        autoComplete="off"
                      />

                      {item.producto_search ? (
                        <button
                          type="button"
                          onMouseDown={(event) => {
                            event.preventDefault()
                            clearProductoSearchForItem(index)
                            setOpenProductoPickerIndex(index)
                          }}
                          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                          aria-label="Limpiar busqueda de producto"
                        >
                          x
                        </button>
                      ) : null}

                      {openProductoPickerIndex === index && (
                        <div className="absolute z-50 mt-1 max-h-56 w-full overflow-auto rounded-md border border-border bg-popover p-1 shadow-lg">
                          {getFilteredProductosForItem(item).length === 0 ? (
                            <p className="px-2 py-2 text-xs text-muted-foreground">
                              No hay coincidencias para "{item.producto_search}".
                            </p>
                          ) : (
                            getFilteredProductosForItem(item).slice(0, 30).map((producto) => (
                              <button
                                key={producto.id}
                                type="button"
                                onMouseDown={(event) => {
                                  event.preventDefault()
                                  selectProductoForItem(index, producto)
                                }}
                                onMouseEnter={() => {
                                  const options = getFilteredProductosForItem(item)
                                  const optionIndex = options.findIndex((opt) => opt.id === producto.id)
                                  setProductoPickerCursor({ itemIndex: index, optionIndex })
                                }}
                                className="flex w-full items-center justify-between rounded px-2 py-2 text-left text-sm hover:bg-muted"
                              >
                                <span className="truncate">{producto.nombre}</span>
                              </button>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                    {itemErrors[index]?.producto && (
                      <span className="mt-1 block text-xs text-destructive">{itemErrors[index]?.producto}</span>
                    )}
                  </label>

                  <label className="text-sm">
                    Impuesto
                    <select
                      className={[
                        'mt-1 w-full rounded-md border bg-background px-3 py-2',
                        itemErrors[index]?.impuesto ? 'border-destructive' : 'border-input',
                      ].join(' ')}
                      value={item.impuesto}
                      onChange={(event) => updateItemField(index, 'impuesto', event.target.value)}
                    >
                      <option value="">Sin impuesto</option>
                      {impuestos.map((impuesto) => (
                        <option key={impuesto.id} value={String(impuesto.id)}>
                          {impuesto.nombre}
                        </option>
                      ))}
                    </select>
                    {itemErrors[index]?.impuesto && (
                      <span className="mt-1 block text-xs text-destructive">{itemErrors[index]?.impuesto}</span>
                    )}
                  </label>

                  <label className="text-sm md:col-span-2">
                    {String(item.tipo || 'PRODUCTO').toUpperCase() === 'SERVICIO'
                      ? 'Descripcion del servicio'
                      : 'Descripcion'}
                    <input
                      className={[
                        'mt-1 w-full rounded-md border bg-background px-3 py-2',
                        itemErrors[index]?.descripcion ? 'border-destructive' : 'border-input',
                      ].join(' ')}
                      value={item.descripcion}
                      onChange={(event) => updateItemField(index, 'descripcion', event.target.value)}
                    />
                    {itemErrors[index]?.descripcion && (
                      <span className="mt-1 block text-xs text-destructive">{itemErrors[index]?.descripcion}</span>
                    )}
                  </label>

                  <label className="text-sm">
                    Cantidad
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      className={[
                        'mt-1 w-full rounded-md border bg-background px-3 py-2',
                        itemErrors[index]?.cantidad ? 'border-destructive' : 'border-input',
                      ].join(' ')}
                      value={item.cantidad}
                      onChange={(event) => updateItemField(index, 'cantidad', event.target.value)}
                    />
                    {itemErrors[index]?.cantidad && (
                      <span className="mt-1 block text-xs text-destructive">{itemErrors[index]?.cantidad}</span>
                    )}
                  </label>

                  <label className="text-sm">
                    Precio unitario
                    <input
                      type="number"
                      min="0"
                      step="1"
                      className={[
                        'mt-1 w-full rounded-md border bg-background px-3 py-2',
                        itemErrors[index]?.precio_unitario ? 'border-destructive' : 'border-input',
                      ].join(' ')}
                      value={item.precio_unitario}
                      onChange={(event) => updateItemField(index, 'precio_unitario', event.target.value)}
                    />
                    {itemErrors[index]?.precio_unitario && (
                      <span className="mt-1 block text-xs text-destructive">{itemErrors[index]?.precio_unitario}</span>
                    )}
                  </label>

                  <label className="text-sm">
                    Descuento item (%)
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      className={[
                        'mt-1 w-full rounded-md border bg-background px-3 py-2',
                        itemErrors[index]?.descuento ? 'border-destructive' : 'border-input',
                      ].join(' ')}
                      value={item.descuento}
                      onChange={(event) => updateItemField(index, 'descuento', event.target.value)}
                    />
                    {itemErrors[index]?.descuento && (
                      <span className="mt-1 block text-xs text-destructive">{itemErrors[index]?.descuento}</span>
                    )}
                  </label>
                </div>}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 rounded-lg border border-border bg-muted/20 p-3">
          <p className="text-sm font-semibold">Resumen estimado</p>
          <div className="mt-2 grid gap-2 text-sm md:grid-cols-2">
            <p className="text-muted-foreground">
              Subtotal items:{' '}
              <span className="font-medium text-foreground">
                {formatMoney(summary.itemSubtotal)}
              </span>
            </p>
            <p className="text-muted-foreground">
              Descuento global:{' '}
              <span className="font-medium text-foreground">
                {formatMoney(summary.descuentoGlobal)}
              </span>
            </p>
            <p className="text-muted-foreground">
              Impuesto estimado:{' '}
              <span className="font-medium text-foreground">
                {formatMoney(summary.impuestoEstimado)}
              </span>
            </p>
            <p className="text-muted-foreground">
              Total estimado:{' '}
              <span className="font-semibold text-primary">
                {formatMoney(summary.totalEstimado)}
              </span>
            </p>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2">
          <Button type="submit" size="md" disabled={status === 'loading'}>
            {status === 'loading' ? 'Guardando...' : 'Guardar cambios'}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/presupuestos')}
            disabled={status === 'loading'}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </section>
  )
}

export default PresupuestosEditPage
