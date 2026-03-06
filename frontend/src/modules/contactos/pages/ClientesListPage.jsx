import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
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

function ClientesListPage() {
  const [clientes, setClientes] = useState([])
  const [contactos, setContactos] = useState([])
  const [status, setStatus] = useState('idle')
  const [search, setSearch] = useState('')
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [clienteToDelete, setClienteToDelete] = useState(null)
  const [editForm, setEditForm] = useState({
    clienteId: null,
    contactoId: null,
    nombre: '',
    razon_social: '',
    rut: '',
    tipo: 'EMPRESA',
    email: '',
    telefono: '',
    celular: '',
    notas: '',
    activo: true,
    limite_credito: 0,
    dias_credito: 0,
    categoria_cliente: '',
    segmento: '',
  })

  const loadData = async () => {
    setStatus('loading')

    try {
      const [{ data: clientesData }, { data: contactosData }] = await Promise.all([
        api.get('/clientes/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
      ])

      setClientes(normalizeListResponse(clientesData))
      setContactos(normalizeListResponse(contactosData))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los clientes.' }))
    }
  }

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => {
      map.set(String(contacto.id), contacto)
    })
    return map
  }, [contactos])

  const filteredClientes = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return clientes
    }

    return clientes.filter((cliente) => {
      const contacto = contactoById.get(String(cliente.contacto))
      const nombre = String(contacto?.nombre || '').toLowerCase()
      const rut = String(contacto?.rut || '').toLowerCase()
      const email = String(contacto?.email || '').toLowerCase()
      return nombre.includes(query) || rut.includes(query) || email.includes(query)
    })
  }, [clientes, contactoById, search])

  const openEditModal = (cliente) => {
    const contacto = contactoById.get(String(cliente.contacto))

    setEditForm({
      clienteId: cliente.id,
      contactoId: contacto?.id || null,
      nombre: contacto?.nombre || '',
      razon_social: contacto?.razon_social || '',
      rut: contacto?.rut || '',
      tipo: contacto?.tipo || 'EMPRESA',
      email: contacto?.email || '',
      telefono: contacto?.telefono || '',
      celular: contacto?.celular || '',
      notas: contacto?.notas || '',
      activo: Boolean(contacto?.activo ?? true),
      limite_credito: toIntegerString(cliente?.limite_credito ?? 0),
      dias_credito: cliente?.dias_credito ?? 0,
      categoria_cliente: cliente?.categoria_cliente || '',
      segmento: cliente?.segmento || '',
    })
    setEditModalOpen(true)
  }

  const updateEditField = (key, value) => {
    setEditForm((prev) => ({ ...prev, [key]: value }))
  }

  const closeEditModal = () => {
    setEditModalOpen(false)
    setSavingEdit(false)
  }

  const handleEditSubmit = async (event) => {
    event.preventDefault()
    if (!editForm.clienteId || !editForm.contactoId) {
      return
    }

    setSavingEdit(true)

    try {
      await api.patch(
        `/contactos/${editForm.contactoId}/`,
        {
          nombre: editForm.nombre,
          razon_social: editForm.razon_social || null,
          rut: editForm.rut || null,
          tipo: editForm.tipo,
          email: editForm.email || null,
          telefono: editForm.telefono || null,
          celular: editForm.celular || null,
          notas: editForm.notas || null,
          activo: Boolean(editForm.activo),
        },
        { suppressGlobalErrorToast: true },
      )

      await api.patch(
        `/clientes/${editForm.clienteId}/`,
        {
          contacto: editForm.contactoId,
          limite_credito: Number(editForm.limite_credito) || 0,
          dias_credito: Number(editForm.dias_credito) || 0,
          categoria_cliente: editForm.categoria_cliente || null,
          segmento: editForm.segmento || null,
          activo: Boolean(editForm.activo),
        },
        { suppressGlobalErrorToast: true },
      )

      toast.success('Cliente actualizado correctamente.')
      closeEditModal()
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el cliente.' }))
      setSavingEdit(false)
    }
  }

  const requestDeleteCliente = (cliente) => {
    setClienteToDelete(cliente)
  }

  const confirmDeleteCliente = async () => {
    const cliente = clienteToDelete
    const contactoId = cliente?.contacto
    if (!cliente?.id || !contactoId) {
      return
    }

    setDeletingId(cliente.id)

    try {
      await api.delete(`/clientes/${cliente.id}/`, { suppressGlobalErrorToast: true })

      const { data: proveedoresData } = await api.get('/proveedores/', {
        suppressGlobalErrorToast: true,
      })
      const proveedores = normalizeListResponse(proveedoresData)
      const contactoEnProveedor = proveedores.some(
        (proveedor) => String(proveedor.contacto) === String(contactoId),
      )

      if (!contactoEnProveedor) {
        await api.delete(`/contactos/${contactoId}/`, { suppressGlobalErrorToast: true })
      }

      toast.success('Cliente eliminado correctamente.')
      setClienteToDelete(null)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el cliente.' }))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Clientes</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <Button variant="outline" size="md" fullWidth className="sm:w-auto" onClick={loadData}>
            Recargar
          </Button>
          <Link
            to="/contactos/clientes/nuevo"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Nuevo cliente
          </Link>
        </div>
      </div>

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:max-w-sm">
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') {
                setSearch('')
              }
            }}
            placeholder="Buscar por nombre, RUT o email..."
            className="w-full rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm"
          />
          {search ? (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Limpiar busqueda"
            >
              x
            </button>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">
          Mostrando {filteredClientes.length} de {clientes.length} clientes
        </p>
      </div>

      {status === 'loading' && <p className="text-sm text-muted-foreground">Cargando clientes...</p>}

      {status === 'succeeded' && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Nombre</th>
                <th className="px-3 py-2 text-left font-medium">RUT</th>
                <th className="px-3 py-2 text-left font-medium">Email</th>
                <th className="px-3 py-2 text-left font-medium">Telefono</th>
                <th className="px-3 py-2 text-left font-medium">Limite credito</th>
                <th className="px-3 py-2 text-left font-medium">Dias credito</th>
                <th className="w-px whitespace-nowrap px-2 py-2 text-left font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredClientes.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={7}>
                    No hay clientes cargados.
                  </td>
                </tr>
              ) : (
                filteredClientes.map((cliente) => {
                  const contacto = contactoById.get(String(cliente.contacto))

                  return (
                    <tr key={cliente.id} className="border-t border-border">
                      <td className="px-3 py-2">{contacto?.nombre || '-'}</td>
                      <td className="px-3 py-2">{contacto?.rut || '-'}</td>
                      <td className="px-3 py-2">{contacto?.email || '-'}</td>
                      <td className="px-3 py-2">{contacto?.telefono || contacto?.celular || '-'}</td>
                      <td className="px-3 py-2">{formatMoney(cliente?.limite_credito ?? 0)}</td>
                      <td className="px-3 py-2">{cliente?.dias_credito ?? 0}</td>
                      <td className="w-px whitespace-nowrap px-2 py-2">
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditModal(cliente)}
                            className="h-7 px-2 text-xs"
                          >
                            Editar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deletingId === cliente.id}
                            onClick={() => requestDeleteCliente(cliente)}
                            className="h-7 border-destructive/40 px-2 text-xs text-destructive hover:bg-destructive/10"
                          >
                            {deletingId === cliente.id ? 'Eliminando...' : 'Eliminar'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {editModalOpen && (
        <div className="fixed inset-0 z-90 flex items-center justify-center bg-foreground/40 p-4">
          <div className="w-full max-w-3xl rounded-xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold">Editar cliente</h3>
              <Button variant="outline" size="sm" onClick={closeEditModal} disabled={savingEdit}>
                Cerrar
              </Button>
            </div>

            <form className="space-y-3" onSubmit={handleEditSubmit}>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-sm">
                  Nombre
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.nombre}
                    onChange={(event) => updateEditField('nombre', event.target.value)}
                    required
                  />
                </label>

                <label className="text-sm">
                  Razon social
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.razon_social}
                    onChange={(event) => updateEditField('razon_social', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  RUT
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.rut}
                    onChange={(event) => updateEditField('rut', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Tipo
                  <select
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.tipo}
                    onChange={(event) => updateEditField('tipo', event.target.value)}
                  >
                    <option value="PERSONA">Persona</option>
                    <option value="EMPRESA">Empresa</option>
                  </select>
                </label>

                <label className="text-sm">
                  Email
                  <input
                    type="email"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.email}
                    onChange={(event) => updateEditField('email', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Telefono
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.telefono}
                    onChange={(event) => updateEditField('telefono', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Celular
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.celular}
                    onChange={(event) => updateEditField('celular', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Limite credito
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.limite_credito}
                    onChange={(event) => updateEditField('limite_credito', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Dias credito
                  <input
                    type="number"
                    min="0"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.dias_credito}
                    onChange={(event) => updateEditField('dias_credito', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Categoria cliente
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.categoria_cliente}
                    onChange={(event) => updateEditField('categoria_cliente', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Segmento
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.segmento}
                    onChange={(event) => updateEditField('segmento', event.target.value)}
                  />
                </label>

                <label className="text-sm md:col-span-2">
                  Notas
                  <textarea
                    rows={3}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.notas}
                    onChange={(event) => updateEditField('notas', event.target.value)}
                  />
                </label>

                <label className="flex items-center gap-2 text-sm md:col-span-2">
                  <input
                    type="checkbox"
                    checked={editForm.activo}
                    onChange={(event) => updateEditField('activo', event.target.checked)}
                  />
                  Activo
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={closeEditModal} disabled={savingEdit}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={savingEdit}>
                  {savingEdit ? 'Guardando...' : 'Guardar cambios'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(clienteToDelete)}
        title="Eliminar cliente"
        description="Se eliminara este cliente. Si el contacto no esta asociado a proveedor tambien se eliminara."
        confirmLabel="Eliminar"
        loading={deletingId === clienteToDelete?.id}
        onCancel={() => {
          if (!deletingId) {
            setClienteToDelete(null)
          }
        }}
        onConfirm={confirmDeleteCliente}
      />
    </section>
  )
}

export default ClientesListPage
