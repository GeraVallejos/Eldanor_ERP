import { useState } from 'react'
import { useDispatch } from 'react-redux'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'
import { productosApi } from '@/modules/productos/store/api'
import { createProducto, fetchProductos, resetCreateProductoState } from '@/modules/productos/productosSlice'

function buildListaPrecioPayload(formLista) {
  const prioridad = Number(String(formLista?.prioridad || '100').trim())

  return {
    nombre: String(formLista?.nombre || '').trim(),
    moneda: formLista?.moneda || null,
    cliente: formLista?.cliente || null,
    fecha_desde: formLista?.fecha_desde || null,
    fecha_hasta: formLista?.fecha_hasta || null,
    prioridad: Number.isFinite(prioridad) ? prioridad : null,
    activa: Boolean(formLista?.activa),
  }
}

function useDeleteProductoAction({ canDelete, onSuccess } = {}) {
  const [deletingId, setDeletingId] = useState(null)

  const deleteProducto = async (producto) => {
    if (!producto?.id) {
      return false
    }
    if (!canDelete) {
      toast.error('No tiene permiso para eliminar productos.')
      return false
    }

    setDeletingId(producto.id)
    try {
      await productosApi.removeOne(productosApi.endpoints.productos, producto.id)
      invalidateProductosCatalogCache()
      toast.success('Producto procesado correctamente.')
      await onSuccess?.(producto)
      return true
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el producto.' }))
      return false
    } finally {
      setDeletingId(null)
    }
  }

  return { deletingId, deleteProducto }
}

function useSaveListaPrecioAction({ canCreate, canEdit, onSuccess } = {}) {
  const [savingLista, setSavingLista] = useState(false)

  const saveLista = async (formLista) => {
    const isEditMode = Boolean(formLista?.id)
    if (!(isEditMode ? canEdit : canCreate)) {
      toast.error('No tiene permiso para guardar listas de precio.')
      return false
    }

    const payload = buildListaPrecioPayload(formLista)
    if (!payload.nombre || !payload.moneda || !payload.fecha_desde) {
      toast.error('Nombre, moneda y vigencia desde son obligatorios.')
      return false
    }
    if (payload.prioridad === null || payload.prioridad < 0) {
      toast.error('La prioridad debe ser un numero positivo.')
      return false
    }

    setSavingLista(true)
    try {
      if (isEditMode) {
        await productosApi.updateOne(productosApi.endpoints.listasPrecio, formLista.id, payload)
        toast.success('Lista de precio actualizada.')
      } else {
        await productosApi.createOne(productosApi.endpoints.listasPrecio, payload)
        toast.success('Lista de precio creada.')
      }
      await onSuccess?.(formLista)
      return true
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo guardar la lista.' }))
      return false
    } finally {
      setSavingLista(false)
    }
  }

  return { savingLista, saveLista }
}

function useDeleteListaPrecioAction({ canDelete, onSuccess } = {}) {
  const [deletingListaId, setDeletingListaId] = useState(null)

  const deleteLista = async (target) => {
    if (!target?.id) {
      return false
    }
    if (!canDelete) {
      toast.error('No tiene permiso para eliminar listas de precio.')
      return false
    }

    setDeletingListaId(target.id)
    try {
      await productosApi.removeOne(productosApi.endpoints.listasPrecio, target.id)
      toast.success('Lista de precio procesada correctamente.')
      await onSuccess?.(target)
      return true
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el registro.' }))
      return false
    } finally {
      setDeletingListaId(null)
    }
  }

  return { deletingListaId, deleteLista }
}

function useSaveProductoAction({ canCreate = true, canEdit = true } = {}) {
  const dispatch = useDispatch()
  const [submitting, setSubmitting] = useState(false)

  const saveProducto = async ({ payload, productoId, isEditMode }) => {
    dispatch(resetCreateProductoState())

    if (isEditMode && !canEdit) {
      toast.error('No tiene permiso para editar productos.')
      return { ok: false, contract: null }
    }
    if (!isEditMode && !canCreate) {
      toast.error('No tiene permiso para crear productos.')
      return { ok: false, contract: null }
    }

    setSubmitting(true)
    try {
      let data
      if (isEditMode) {
        data = await productosApi.updateOne(productosApi.endpoints.productos, productoId, payload)
      } else {
        data = await dispatch(createProducto(payload)).unwrap()
      }

      invalidateProductosCatalogCache()
      toast.success(isEditMode ? 'Producto actualizado correctamente.' : 'Producto creado correctamente.')
      dispatch(fetchProductos())
      dispatch(resetCreateProductoState())

      return { ok: true, data }
    } catch (error) {
      const fallback = isEditMode ? 'No se pudo actualizar el producto.' : 'No se pudo crear el producto.'
      const message = isEditMode
        ? normalizeApiError(error, { fallback })
        : typeof error === 'string'
          ? error
          : (error?.message || fallback)
      toast.error(message)
      return {
        ok: false,
        error,
        contract: error?.response?.data || (typeof error === 'object' ? error : null),
      }
    } finally {
      setSubmitting(false)
    }
  }

  return { submitting, saveProducto }
}

export {
  useDeleteListaPrecioAction,
  useDeleteProductoAction,
  useSaveListaPrecioAction,
  useSaveProductoAction,
}
