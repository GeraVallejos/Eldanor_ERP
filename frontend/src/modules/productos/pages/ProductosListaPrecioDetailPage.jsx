import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import ActiveSearchFilter from '@/components/ui/ActiveSearchFilter'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import SearchableSelect from '@/components/ui/SearchableSelect'
import TablePagination from '@/components/ui/TablePagination'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatSmartNumber } from '@/lib/numberFormat'
import { useResponsiveTablePageSize } from '@/lib/useResponsiveTablePageSize'
import { cn } from '@/lib/utils'
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

function emptyItemForm() {
  return { id: null, producto: '', precio: '', descuento_maximo: '0' }
}

function formatPriorityDisplay(lista) {
  const labels = {
    10: 'Urgente',
    50: 'Alta',
    100: 'Normal',
    200: 'Respaldo',
  }
  const value = Number(lista?.prioridad ?? 0)
  return labels[value] || 'Personalizada'
}

function ProductosListaPrecioDetailPage() {
  const { id } = useParams()
  const itemsPageSize = useResponsiveTablePageSize({ mobileRows: 6, reservedHeight: 640, desktopMaxRows: 9 })
  const permissions = usePermissions(['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'])
  const [status, setStatus] = useState('idle')
  const [lista, setLista] = useState(null)
  const [items, setItems] = useState([])
  const [itemsTotalCount, setItemsTotalCount] = useState(0)
  const [baseItemsTotalCount, setBaseItemsTotalCount] = useState(0)
  const [productos, setProductos] = useState([])
  const [productoSearch, setProductoSearch] = useState('')
  const [loadingProductos, setLoadingProductos] = useState(false)
  const [loadingItems, setLoadingItems] = useState(false)
  const [savingItem, setSavingItem] = useState(false)
  const [deletingTarget, setDeletingTarget] = useState(null)
  const [itemsPage, setItemsPage] = useState(1)
  const [formItem, setFormItem] = useState(emptyItemForm)

  const handleProductoSearchChange = useCallback((value) => {
    setItemsPage(1)
    setProductoSearch(value)
  }, [])

  const loadLista = useCallback(async () => {
    try {
      const { data } = await api.get(`/listas-precio/${id}/`, { suppressGlobalErrorToast: true })
      setLista(data)
    } catch (error) {
      throw error
    }
  }, [id])

  const loadItems = useCallback(async ({ page = 1, query = '' } = {}) => {
    setLoadingItems(true)
    try {
      const normalizedQuery = String(query || '').trim()
      const { data } = await api.get('/listas-precio-items/', {
        params: {
          lista: id,
          page,
          page_size: itemsPageSize,
          ...(normalizedQuery ? { q: normalizedQuery } : {}),
        },
        suppressGlobalErrorToast: true,
      })
      const nextItems = normalizeListResponse(data)
      const totalCount = Number(data?.count ?? nextItems.length)
      setItems(nextItems)
      setItemsTotalCount(totalCount)
      if (!normalizedQuery) {
        setBaseItemsTotalCount(totalCount)
      }
      if (page > 1 && nextItems.length === 0 && totalCount > 0) {
        setItemsPage((prev) => Math.max(1, prev - 1))
      }
    } finally {
      setLoadingItems(false)
    }
  }, [id, itemsPageSize])

  useEffect(() => {
    let active = true

    const loadPage = async () => {
      setStatus('loading')
      try {
        await Promise.all([loadLista(), loadItems({ page: 1, query: '' })])
        if (!active) {
          return
        }
        setStatus('succeeded')
      } catch (error) {
        if (!active) {
          return
        }
        setStatus('failed')
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la lista de precio.' }))
      }
    }

    void loadPage()

    return () => {
      active = false
    }
  }, [loadItems, loadLista])

  useEffect(() => {
    if (status === 'idle' || status === 'loading') {
      return
    }
    void loadItems({ page: itemsPage, query: productoSearch })
  }, [itemsPage, itemsPageSize, loadItems, productoSearch, status])

  useEffect(() => {
    const timeoutId = setTimeout(async () => {
      setLoadingProductos(true)
      try {
        const params = {}
        const normalizedSearch = String(productoSearch || '').trim()
        if (normalizedSearch) {
          params.q = normalizedSearch
        }
        const { data } = await api.get('/productos/', {
          params,
          suppressGlobalErrorToast: true,
        })
        setProductos(normalizeListResponse(data))
      } catch (error) {
        toast.error(normalizeApiError(error, { fallback: 'No se pudo buscar productos para la lista.' }))
      } finally {
        setLoadingProductos(false)
      }
    }, 250)

    return () => clearTimeout(timeoutId)
  }, [productoSearch])

  const productoLabelById = useMemo(() => {
    const map = new Map()
    productos.forEach((producto) => {
      map.set(
        String(producto.id),
        producto.nombre || producto.sku || 'Producto sin nombre',
      )
    })
    return map
  }, [productos])

  const itemsPageCount = useMemo(
    () => Math.max(1, Math.ceil(itemsTotalCount / itemsPageSize)),
    [itemsTotalCount, itemsPageSize],
  )

  useEffect(() => {
    setItemsPage(1)
  }, [itemsPageSize])

  useEffect(() => {
    setItemsPage((prev) => Math.min(prev, Math.max(1, itemsPageCount)))
  }, [itemsPageCount])

  const productoOptions = useMemo(() => {
    const remoteOptions = productos.map((producto) => ({
      value: String(producto.id),
      label: producto.nombre || producto.sku || 'Producto sin nombre',
      keywords: `${producto.sku || ''} ${producto.nombre || ''}`,
    }))
    const selectedItem = items.find((item) => String(item.producto) === String(formItem.producto))
    if (selectedItem && !remoteOptions.some((option) => option.value === String(selectedItem.producto))) {
      remoteOptions.unshift({
        value: String(selectedItem.producto),
        label:
          selectedItem.producto_nombre
          || productoLabelById.get(String(selectedItem.producto))
          || 'Producto seleccionado',
        keywords: `${selectedItem.producto_nombre || ''} ${productoLabelById.get(String(selectedItem.producto)) || ''}`,
      })
    }
    return remoteOptions
  }, [formItem.producto, items, productoLabelById, productos])

  const resetItemForm = () => setFormItem(emptyItemForm())

  const startEditItem = (item) => {
    setFormItem({
      id: item.id,
      producto: String(item.producto || ''),
      precio: String(item.precio ?? ''),
      descuento_maximo: String(item.descuento_maximo ?? '0'),
    })
  }

  const submitItem = async (event) => {
    event.preventDefault()
    if (!(formItem.id ? permissions['PRODUCTOS.EDITAR'] : permissions['PRODUCTOS.CREAR'])) {
      toast.error('No tiene permiso para guardar precios de lista.')
      return
    }

    const payload = {
      lista: id,
      producto: formItem.producto,
      precio: formItem.precio,
      descuento_maximo: formItem.descuento_maximo || '0',
    }

    if (!payload.producto || !payload.precio) {
      toast.error('Producto y precio son obligatorios.')
      return
    }

    setSavingItem(true)
    try {
      if (formItem.id) {
        await api.patch(`/listas-precio-items/${formItem.id}/`, payload, { suppressGlobalErrorToast: true })
        toast.success('Precio actualizado en la lista.')
      } else {
        await api.post('/listas-precio-items/', payload, { suppressGlobalErrorToast: true })
        toast.success('Precio agregado a la lista.')
      }
      resetItemForm()
      handleProductoSearchChange('')
      await loadItems({ page: 1, query: '' })
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar el precio.' }))
    } finally {
      setSavingItem(false)
    }
  }

  const confirmDelete = async () => {
    if (!deletingTarget) {
      return
    }
    if (!permissions['PRODUCTOS.BORRAR']) {
      toast.error('No tiene permiso para eliminar precios de lista.')
      return
    }

    try {
      await api.delete(`/listas-precio-items/${deletingTarget.id}/`, { suppressGlobalErrorToast: true })
      toast.success('Precio eliminado de la lista.')
      setDeletingTarget(null)
      await loadItems({ page: itemsPage, query: productoSearch })
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el registro.' }))
    }
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando lista de precio...</p>
  }

  if (status === 'failed') {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Detalle de lista de precio</h2>
            <p className="text-sm text-muted-foreground">No fue posible recuperar la lista solicitada.</p>
          </div>
          <Link to="/productos/listas-precio" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
        </div>
      </section>
    )
  }

  if (!lista) {
    return null
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Lista de precio</p>
          <h2 className="mt-1 text-3xl font-semibold">{lista.nombre}</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {lista.cliente_nombre || 'Lista general'} | {lista.moneda_codigo || '-'} | {formatPriorityDisplay(lista)} | {lista.activa ? 'Activa' : 'Inactiva'}
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/productos/listas-precio" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver a listas
          </Link>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <div className="grid gap-3 text-sm md:grid-cols-4">
          <p><span className="font-medium">Cliente:</span> {lista.cliente_nombre || 'Lista general'}</p>
          <p><span className="font-medium">Moneda:</span> {lista.moneda_codigo || '-'}</p>
          <p><span className="font-medium">Vigencia:</span> {lista.fecha_desde || '-'} {lista.fecha_hasta ? `a ${lista.fecha_hasta}` : 'sin termino'}</p>
          <p><span className="font-medium">Estado:</span> {lista.activa ? 'Activa' : 'Inactiva'}</p>
        </div>
      </div>

      <div className="space-y-3 rounded-md border border-border bg-card p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold">Precios por producto</h3>
            <p className="text-sm text-muted-foreground">Cargue precios individuales o realice importaciones masivas por SKU para esta lista.</p>
          </div>
          {permissions['PRODUCTOS.EDITAR'] ? (
            <BulkImportButton
              endpoint={`/listas-precio/${id}/bulk_import/`}
              templateEndpoint={`/listas-precio/${id}/bulk_template/`}
              previewBeforeImport
              previewTitle="Confirmar carga masiva de precios"
              onCompleted={() => {
                resetItemForm()
                handleProductoSearchChange('')
                void loadItems({ page: 1, query: '' })
              }}
            />
          ) : null}
        </div>

        {productoSearch.trim() ? (
          <ActiveSearchFilter
            query={productoSearch}
            filteredCount={itemsTotalCount}
            totalCount={baseItemsTotalCount}
            noun="precios"
            onClear={() => handleProductoSearchChange('')}
          />
        ) : null}

        <form className="grid gap-3 md:grid-cols-3" onSubmit={submitItem}>
          <label className="text-sm">
            Producto
            <SearchableSelect
              className="mt-1"
              value={formItem.producto}
              onChange={(value) => setFormItem((prev) => ({ ...prev, producto: value }))}
              onSearchChange={handleProductoSearchChange}
              options={productoOptions}
              placeholder="Buscar producto..."
              ariaLabel="Producto"
              loading={loadingProductos}
              emptyText="No hay productos coincidentes"
            />
          </label>
          <label className="text-sm">
            Precio
            <input type="number" min="0" step="0.01" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formItem.precio} onChange={(event) => setFormItem((prev) => ({ ...prev, precio: event.target.value }))} required />
          </label>
          <label className="text-sm">
            Descuento maximo
            <input type="number" min="0" max="100" step="0.01" className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2" value={formItem.descuento_maximo} onChange={(event) => setFormItem((prev) => ({ ...prev, descuento_maximo: event.target.value }))} />
          </label>
          <div className="flex gap-2 md:col-span-3">
            <Button type="submit" disabled={savingItem}>{savingItem ? 'Guardando...' : (formItem.id ? 'Actualizar precio' : 'Agregar precio')}</Button>
            {formItem.id ? <Button type="button" variant="outline" onClick={resetItemForm}>Cancelar</Button> : null}
          </div>
        </form>

        <div className="overflow-x-auto rounded-md border border-border">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Producto</th>
                <th className="px-3 py-2 text-left font-medium">Precio</th>
                <th className="px-3 py-2 text-left font-medium">Desc. max.</th>
                <th className="px-3 py-2 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loadingItems ? (
                <tr><td className="px-3 py-3 text-muted-foreground" colSpan={4}>Cargando precios...</td></tr>
              ) : items.length === 0 ? (
                <tr><td className="px-3 py-3 text-muted-foreground" colSpan={4}>La lista seleccionada no tiene items para este filtro.</td></tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="border-t border-border">
                    <td className="px-3 py-2">{item.producto_nombre || productoLabelById.get(String(item.producto)) || 'Producto sin nombre'}</td>
                    <td className="px-3 py-2">{formatSmartNumber(item.precio ?? 0, { maximumFractionDigits: 2 })}</td>
                    <td className="px-3 py-2">{formatSmartNumber(item.descuento_maximo ?? 0, { maximumFractionDigits: 2 })}%</td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-2">
                        {permissions['PRODUCTOS.EDITAR'] ? <Button type="button" size="sm" variant="outline" onClick={() => startEditItem(item)}>Editar</Button> : null}
                        {permissions['PRODUCTOS.BORRAR'] ? <Button type="button" size="sm" variant="outline" className="border-destructive/40 text-destructive hover:bg-destructive/10" onClick={() => setDeletingTarget({ id: item.id, label: item.producto_nombre || productoLabelById.get(String(item.producto)) || 'Producto sin nombre' })}>Eliminar</Button> : null}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {itemsTotalCount > 0 ? (
          <TablePagination
            currentPage={itemsPage}
            totalPages={itemsPageCount}
            totalRows={itemsTotalCount}
            pageSize={itemsPageSize}
            onPrev={() => setItemsPage((prev) => Math.max(1, prev - 1))}
            onNext={() => setItemsPage((prev) => Math.min(itemsPageCount, prev + 1))}
          />
        ) : null}
      </div>

      <ConfirmDialog
        open={Boolean(deletingTarget)}
        title="Eliminar precio configurado"
        description={
          deletingTarget
            ? `Se eliminara la configuracion de precio para "${deletingTarget.label}".`
            : ''
        }
        confirmLabel="Confirmar"
        onCancel={() => setDeletingTarget(null)}
        onConfirm={confirmDelete}
      />
    </section>
  )
}

export default ProductosListaPrecioDetailPage
