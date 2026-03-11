import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import TablePagination from '@/components/ui/TablePagination'
import { useTableSorting } from '@/lib/tableSorting'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { selectCurrentUser } from '@/modules/auth/authSlice'

function normalizeListResponse(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.results)) {
    return data.results
  }

  return []
}

function ProveedoresListPage() {
  const currentUser = useSelector(selectCurrentUser)
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [status, setStatus] = useState('idle')
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [proveedorToDelete, setProveedorToDelete] = useState(null)
  const [editForm, setEditForm] = useState({
    proveedorId: null,
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
    giro: '',
    vendedor_contacto: '',
    dias_credito: 0,
  })

  const loadData = async () => {
    setStatus('loading')

    const params = canViewInactive && includeInactive ? { include_inactive: '1' } : undefined

    try {
      const [{ data: proveedoresData }, { data: contactosData }] = await Promise.all([
        api.get('/proveedores/', { params, suppressGlobalErrorToast: true }),
        api.get('/contactos/', { params, suppressGlobalErrorToast: true }),
      ])

      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los proveedores.' }))
    }
  }

  const userRole = String(currentUser?.rol || '').toUpperCase()
  const canViewInactive = userRole === 'OWNER' || userRole === 'ADMIN'
  const canBulkImport = userRole === 'ADMIN'

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [includeInactive, canViewInactive])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => {
      map.set(String(contacto.id), contacto)
    })
    return map
  }, [contactos])

  const filteredProveedores = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return proveedores
    }

    return proveedores.filter((proveedor) => {
      const contacto = contactoById.get(String(proveedor.contacto))
      const nombre = String(contacto?.nombre || '').toLowerCase()
      const rut = String(contacto?.rut || '').toLowerCase()
      const email = String(contacto?.email || '').toLowerCase()
      return nombre.includes(query) || rut.includes(query) || email.includes(query)
    })
  }, [proveedores, contactoById, search])

  const { paginatedRows: paginatedProveedores, toggleSort, getSortIndicator, currentPage, totalPages, totalRows, pageSize, nextPage, prevPage } = useTableSorting(filteredProveedores, {
    accessors: {
      creado_en: (proveedor) => proveedor.creado_en,
      nombre: (proveedor) => contactoById.get(String(proveedor.contacto))?.nombre || '',
      rut: (proveedor) => contactoById.get(String(proveedor.contacto))?.rut || '',
      email: (proveedor) => contactoById.get(String(proveedor.contacto))?.email || '',
      estado: (proveedor) => (contactoById.get(String(proveedor.contacto))?.activo ? 'Activo' : 'Inactivo'),
      telefono: (proveedor) => {
        const contacto = contactoById.get(String(proveedor.contacto))
        return contacto?.telefono || contacto?.celular || ''
      },
      giro: (proveedor) => proveedor?.giro || '',
      dias_credito: (proveedor) => Number(proveedor?.dias_credito ?? 0),
    },
    initialKey: 'creado_en',
    initialDirection: 'desc',
  })

  const openEditModal = (proveedor) => {
    const contacto = contactoById.get(String(proveedor.contacto))

    setEditForm({
      proveedorId: proveedor.id,
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
      giro: proveedor?.giro || '',
      vendedor_contacto: proveedor?.vendedor_contacto || '',
      dias_credito: proveedor?.dias_credito ?? 0,
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
    if (!editForm.proveedorId || !editForm.contactoId) {
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
        `/proveedores/${editForm.proveedorId}/`,
        {
          contacto: editForm.contactoId,
          giro: editForm.giro || null,
          vendedor_contacto: editForm.vendedor_contacto || null,
          dias_credito: Number(editForm.dias_credito) || 0,
          activo: Boolean(editForm.activo),
        },
        { suppressGlobalErrorToast: true },
      )

      toast.success('Proveedor actualizado correctamente.')
      closeEditModal()
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el proveedor.' }))
      setSavingEdit(false)
    }
  }

  const requestDeleteProveedor = (proveedor) => {
    setProveedorToDelete(proveedor)
  }

  const confirmDeleteProveedor = async () => {
    const proveedor = proveedorToDelete
    const contactoId = proveedor?.contacto
    if (!proveedor?.id || !contactoId) {
      return
    }

    setDeletingId(proveedor.id)

    try {
      await api.delete(`/proveedores/${proveedor.id}/`, { suppressGlobalErrorToast: true })

      const { data: clientesData } = await api.get('/clientes/', {
        suppressGlobalErrorToast: true,
      })
      const clientes = normalizeListResponse(clientesData)
      const contactoEnCliente = clientes.some(
        (cliente) => String(cliente.contacto) === String(contactoId),
      )

      if (!contactoEnCliente) {
        await api.delete(`/contactos/${contactoId}/`, { suppressGlobalErrorToast: true })
      }

      toast.success('Proveedor eliminado correctamente.')
      setProveedorToDelete(null)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el proveedor.' }))
    } finally {
      setDeletingId(null)
    }
  }

  const getTodaySuffix = () => new Date().toISOString().slice(0, 10)

  const handleExportExcel = async () => {
    if (filteredProveedores.length === 0) {
      return
    }

    await downloadExcelFile({
      sheetName: 'Proveedores',
      fileName: `proveedores_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: 'Nombre', key: 'nombre', width: 32 },
        { header: 'RUT', key: 'rut', width: 18 },
        { header: 'Email', key: 'email', width: 28 },
        { header: 'Telefono', key: 'telefono', width: 18 },
        { header: 'Giro', key: 'giro', width: 24 },
        { header: 'Dias credito', key: 'dias_credito', width: 14 },
      ],
      rows: filteredProveedores.map((proveedor) => {
        const contacto = contactoById.get(String(proveedor.contacto))
        return {
          nombre: contacto?.nombre || '-',
          rut: contacto?.rut || '-',
          email: contacto?.email || '-',
          telefono: contacto?.telefono || contacto?.celular || '-',
          giro: proveedor?.giro || '-',
          dias_credito: Number(proveedor?.dias_credito ?? 0),
        }
      }),
    })
  }

  const handleExportPdf = async () => {
    if (filteredProveedores.length === 0) {
      return
    }

    await downloadSimpleTablePdf({
      title: 'Reporte de proveedores',
      fileName: `proveedores_${getTodaySuffix()}.pdf`,
      headers: ['Nombre', 'RUT', 'Email', 'Telefono', 'Giro', 'Dias credito'],
      rows: filteredProveedores.map((proveedor) => {
        const contacto = contactoById.get(String(proveedor.contacto))
        return [
          contacto?.nombre || '-',
          contacto?.rut || '-',
          contacto?.email || '-',
          contacto?.telefono || contacto?.celular || '-',
          proveedor?.giro || '-',
          String(proveedor?.dias_credito ?? 0),
        ]
      }),
    })
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Proveedores</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          {canBulkImport ? (
            <BulkImportButton
              endpoint="/proveedores/bulk_import/"
              templateEndpoint="/proveedores/bulk_template/"
              onCompleted={() => {
                void loadData()
              }}
            />
          ) : null}
          <Button
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onClick={handleExportExcel}
            disabled={filteredProveedores.length === 0}
          >
            Exportar Excel
          </Button>
          <Button
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onClick={handleExportPdf}
            disabled={filteredProveedores.length === 0}
          >
            Exportar PDF
          </Button>
          <Link
            to="/contactos/proveedores/nuevo"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Nuevo proveedor
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
        {canViewInactive ? (
          <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={includeInactive}
              onChange={(event) => setIncludeInactive(event.target.checked)}
            />
            Mostrar inactivos
          </label>
        ) : null}
        <p className="text-xs text-muted-foreground">
          Mostrando {filteredProveedores.length} de {proveedores.length} proveedores
        </p>
      </div>

      {status === 'loading' && <p className="text-sm text-muted-foreground">Cargando proveedores...</p>}

      {status === 'succeeded' && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('nombre')} className="inline-flex items-center gap-1 hover:text-primary">Nombre <span className="text-xs text-muted-foreground">{getSortIndicator('nombre')}</span></button></th>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('rut')} className="inline-flex items-center gap-1 hover:text-primary">RUT <span className="text-xs text-muted-foreground">{getSortIndicator('rut')}</span></button></th>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('email')} className="inline-flex items-center gap-1 hover:text-primary">Email <span className="text-xs text-muted-foreground">{getSortIndicator('email')}</span></button></th>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('estado')} className="inline-flex items-center gap-1 hover:text-primary">Estado <span className="text-xs text-muted-foreground">{getSortIndicator('estado')}</span></button></th>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('telefono')} className="inline-flex items-center gap-1 hover:text-primary">Telefono <span className="text-xs text-muted-foreground">{getSortIndicator('telefono')}</span></button></th>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('giro')} className="inline-flex items-center gap-1 hover:text-primary">Giro <span className="text-xs text-muted-foreground">{getSortIndicator('giro')}</span></button></th>
                <th className="px-3 py-2 text-left font-medium"><button type="button" onClick={() => toggleSort('dias_credito')} className="inline-flex items-center gap-1 hover:text-primary">Dias credito <span className="text-xs text-muted-foreground">{getSortIndicator('dias_credito')}</span></button></th>
                <th className="w-px whitespace-nowrap px-2 py-2 text-left font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredProveedores.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={8}>
                    No hay proveedores cargados.
                  </td>
                </tr>
              ) : (
                paginatedProveedores.map((proveedor) => {
                  const contacto = contactoById.get(String(proveedor.contacto))

                  return (
                    <tr key={proveedor.id} className="border-t border-border">
                      <td className="px-3 py-2">{contacto?.nombre || '-'}</td>
                      <td className="px-3 py-2">{contacto?.rut || '-'}</td>
                      <td className="px-3 py-2">{contacto?.email || '-'}</td>
                      <td className="px-3 py-2">{contacto?.activo ? 'Activo' : 'Inactivo'}</td>
                      <td className="px-3 py-2">{contacto?.telefono || contacto?.celular || '-'}</td>
                      <td className="px-3 py-2">{proveedor?.giro || '-'}</td>
                      <td className="px-3 py-2">{proveedor?.dias_credito ?? 0}</td>
                      <td className="w-px whitespace-nowrap px-2 py-2">
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditModal(proveedor)}
                            className="h-7 px-2 text-xs"
                          >
                            Editar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={deletingId === proveedor.id}
                            onClick={() => requestDeleteProveedor(proveedor)}
                            className="h-7 border-destructive/40 px-2 text-xs text-destructive hover:bg-destructive/10"
                          >
                            {deletingId === proveedor.id ? 'Eliminando...' : 'Eliminar'}
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

      <TablePagination
        currentPage={currentPage}
        totalPages={totalPages}
        totalRows={totalRows}
        pageSize={pageSize}
        onPrev={prevPage}
        onNext={nextPage}
      />

      {editModalOpen && (
        <div className="fixed inset-0 z-90 flex items-center justify-center bg-foreground/40 p-4">
          <div className="w-full max-w-3xl rounded-xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold">Editar proveedor</h3>
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
                  Giro
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.giro}
                    onChange={(event) => updateEditField('giro', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Contacto vendedor
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.vendedor_contacto}
                    onChange={(event) => updateEditField('vendedor_contacto', event.target.value)}
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
        open={Boolean(proveedorToDelete)}
        title="Eliminar proveedor"
        description="Se eliminara este proveedor. Si el contacto no esta asociado a cliente tambien se eliminara."
        confirmLabel="Eliminar"
        loading={deletingId === proveedorToDelete?.id}
        onCancel={() => {
          if (!deletingId) {
            setProveedorToDelete(null)
          }
        }}
        onConfirm={confirmDeleteProveedor}
      />
    </section>
  )
}

export default ProveedoresListPage
