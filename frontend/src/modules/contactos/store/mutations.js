import { useState } from 'react'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import { contactosApi } from '@/modules/contactos/store/api'

function buildContactoPayload(form) {
  return {
    nombre: form.nombre,
    razon_social: form.razon_social || null,
    rut: form.rut || null,
    tipo: form.tipo,
    email: form.email || null,
    telefono: form.telefono || null,
    celular: form.celular || null,
    notas: form.notas || null,
    activo: Boolean(form.activo),
  }
}

function useCreateTerceroAction({
  kind,
  successMessage,
  errorMessage,
  buildPayload,
  onSuccess,
} = {}) {
  const [status, setStatus] = useState('idle')

  const saveTercero = async (form) => {
    setStatus('loading')

    try {
      const endpoint = kind === 'proveedor'
        ? `${contactosApi.endpoints.proveedores}crear-con-contacto/`
        : `${contactosApi.endpoints.clientes}crear-con-contacto/`

      await contactosApi.createOne(endpoint, {
        ...buildContactoPayload(form),
        ...buildPayload(form, null),
      })
      toast.success(successMessage)
      await onSuccess?.()
      return true
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: errorMessage }))
      return false
    } finally {
      setStatus('idle')
    }
  }

  return {
    status,
    saveTercero,
  }
}

function useUpdateTerceroAction({
  kind,
  successMessage,
  errorMessage,
  buildPayload,
  onSuccess,
} = {}) {
  const [status, setStatus] = useState('idle')

  const saveTercero = async ({ form, contactoId, terceroId }) => {
    setStatus('loading')

    try {
      const endpoint = kind === 'proveedor'
        ? contactosApi.endpoints.proveedores
        : contactosApi.endpoints.clientes

      await contactosApi.updateOneWithAction(endpoint, terceroId, 'actualizar-con-contacto', {
        ...buildContactoPayload(form),
        ...buildPayload(form, contactoId),
      })
      toast.success(successMessage)
      await onSuccess?.()
      return { ok: true }
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: errorMessage }))
      return {
        ok: false,
        error,
        contract: error?.response?.data || (typeof error === 'object' ? error : null),
      }
    } finally {
      setStatus('idle')
    }
  }

  return {
    status,
    saveTercero,
  }
}

export {
  useCreateTerceroAction,
  useUpdateTerceroAction,
}
