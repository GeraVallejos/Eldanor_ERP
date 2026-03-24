import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import ActiveSearchFilter from '@/components/ui/ActiveSearchFilter'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import MenuButton from '@/components/ui/MenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import TablePagination from '@/components/ui/TablePagination'
import { getChileDateSuffix } from '@/lib/dateTimeFormat'
import { useTableSorting } from '@/lib/tableSorting'
import { useResponsiveTablePageSize } from '@/lib/useResponsiveTablePageSize'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import { contactosApi } from '@/modules/contactos/store/api'
import { useContactosListado } from '@/modules/contactos/store/hooks'
import { hasAnyRole } from '@/modules/shared/auth/roles'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function ProveedoresListPage() {
  const pageSize = useResponsiveTablePageSize({ reservedHeight: 450 })
  const currentUser = useSelector(selectCurrentUser)
  const permissions = usePermissions(['CONTACTOS.CREAR', 'CONTACTOS.EDITAR', 'CONTACTOS.BORRAR'])
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [proveedorToDelete, setProveedorToDelete] = useState(null)

  const canViewInactive = hasAnyRole(currentUser, ['OWNER', 'ADMIN'])
  const canBulkImport = permissions['CONTACTOS.CREAR'] && hasAnyRole(currentUser, ['ADMIN'])
  const canCreate = permissions['CONTACTOS.CREAR']
  const canEdit = permissions['CONTACTOS.EDITAR']
  const canDelete = permissions['CONTACTOS.BORRAR']
  const {
    rows: proveedores,
    status,
    error,
    reload: loadData,
  } = useContactosListado({
    resource: 'proveedores',
    includeInactive: canViewInactive && includeInactive,
  })

  useEffect(() => {
    if (status === 'failed' && error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudieron cargar los proveedores.' }))
    }
  }, [error, status])

  const filteredProveedores = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return proveedores
    }

    return proveedores.filter((proveedor) => {
      const contacto = proveedor?.contacto_resumen
      const nombre = String(contacto?.nombre || '').toLowerCase()
      const rut = String(contacto?.rut || '').toLowerCase()
      const email = String(contacto?.email || '').toLowerCase()
      return nombre.includes(query) || rut.includes(query) || email.includes(query)
    })
  }, [proveedores, search])

  const { paginatedRows: paginatedProveedores, toggleSort, getSortIndicator, currentPage, totalPages, totalRows, nextPage, prevPage } = useTableSorting(filteredProveedores, {
    accessors: {
      creado_en: (proveedor) => proveedor.creado_en,
      nombre: (proveedor) => proveedor?.contacto_resumen?.nombre || '',
      rut: (proveedor) => proveedor?.contacto_resumen?.rut || '',
      email: (proveedor) => proveedor?.contacto_resumen?.email || '',
      estado: (proveedor) => (proveedor?.contacto_resumen?.activo ? 'Activo' : 'Inactivo'),
      telefono: (proveedor) => {
        const contacto = proveedor?.contacto_resumen
        return contacto?.telefono || contacto?.celular || ''
      },
      giro: (proveedor) => proveedor?.giro || '',
      dias_credito: (proveedor) => Number(proveedor?.dias_credito ?? 0),
    },
    initialKey: 'creado_en',
    initialDirection: 'desc',
    pageSize,
  })

  const requestDeleteProveedor = (proveedor) => {
    setProveedorToDelete(proveedor)
  }

  const confirmDeleteProveedor = async () => {
    const proveedor = proveedorToDelete
    if (!proveedor?.id) {
      return
    }

    setDeletingId(proveedor.id)

    try {
      await contactosApi.removeOne(contactosApi.endpoints.proveedores, proveedor.id)

      toast.success('Proveedor eliminado correctamente.')
      setProveedorToDelete(null)
      await loadData()
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el proveedor.' }))
    } finally {
      setDeletingId(null)
    }
  }

  const getTodaySuffix = () => getChileDateSuffix()

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
        const contacto = proveedor?.contacto_resumen
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
        const contacto = proveedor?.contacto_resumen
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
              previewBeforeImport
              onCompleted={() => {
                void loadData()
              }}
            />
          ) : null}
          <MenuButton
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
            disabled={filteredProveedores.length === 0}
          />
          {canCreate ? (
            <Link
              to="/contactos/proveedores/nuevo"
              className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
            >
              Nuevo proveedor
            </Link>
          ) : null}
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

      <ActiveSearchFilter
        query={search}
        filteredCount={filteredProveedores.length}
        totalCount={proveedores.length}
        noun="proveedores"
        onClear={() => setSearch('')}
      />

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
                  const contacto = proveedor?.contacto_resumen

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
                          <Link
                            to={`/contactos/terceros/${proveedor.contacto}`}
                            className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-7 px-2 text-xs')}
                          >
                            Ver
                          </Link>
                          {canEdit ? (
                            <Link
                              to={`/contactos/proveedores/${proveedor.id}/editar`}
                              className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-7 px-2 text-xs')}
                            >
                              Editar
                            </Link>
                          ) : null}
                          {canDelete ? (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={deletingId === proveedor.id}
                              onClick={() => requestDeleteProveedor(proveedor)}
                              className="h-7 border-destructive/40 px-2 text-xs text-destructive hover:bg-destructive/10"
                            >
                              {deletingId === proveedor.id ? 'Eliminando...' : 'Eliminar'}
                            </Button>
                          ) : null}
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

      <ConfirmDialog
        open={Boolean(proveedorToDelete)}
        title="Eliminar proveedor"
        description="Se eliminara la ficha del proveedor. Si el contacto queda sin relacion comercial, el backend tambien lo limpiara."
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
