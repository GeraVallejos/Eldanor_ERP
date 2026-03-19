import { useEffect, useMemo, useState } from 'react'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import MenuButton from '@/components/ui/MenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import TablePagination from '@/components/ui/TablePagination'
import { getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { invalidateProductosCatalogCache } from '@/modules/productos/services/productosCatalogCache'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import {
  fetchCatalogosProducto,
  fetchProductos,
  selectCategorias,
  selectProductos,
  selectProductosError,
  selectProductosStatus,
} from '@/modules/productos/productosSlice'
import { selectCurrentUser } from '@/modules/auth/authSlice'

const columnHelper = createColumnHelper()

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function ProductosListPage() {
  const dispatch = useDispatch()
  const productos = useSelector(selectProductos)
  const categorias = useSelector(selectCategorias)
  const currentUser = useSelector(selectCurrentUser)
  const status = useSelector(selectProductosStatus)
  const error = useSelector(selectProductosError)
  const [sorting, setSorting] = useState([{ id: 'creado_en', desc: true }])
  const [globalFilter, setGlobalFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 20 })
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [savingEdit, setSavingEdit] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [productoToDelete, setProductoToDelete] = useState(null)
  const [includeInactive, setIncludeInactive] = useState(false)
  const [editForm, setEditForm] = useState({
    id: null,
    nombre: '',
    descripcion: '',
    sku: '',
    tipo: 'PRODUCTO',
    precio_referencia: 0,
    precio_costo: 0,
    maneja_inventario: true,
    stock_actual: 0,
    activo: true,
  })

  const userRole = String(currentUser?.rol || '').toUpperCase()
  const canViewInactive = userRole === 'OWNER' || userRole === 'ADMIN'
  const canBulkImport = userRole === 'ADMIN'

  useEffect(() => {
    dispatch(fetchProductos({ includeInactive: canViewInactive && includeInactive }))
  }, [dispatch, canViewInactive, includeInactive])

  useEffect(() => {
    dispatch(fetchCatalogosProducto())
  }, [dispatch])

  const categoriaLabelById = useMemo(() => {
    const map = new Map()
    categorias.forEach((categoria) => {
      map.set(String(categoria.id), categoria.nombre || '-')
    })
    return map
  }, [categorias])

  const categoryOptions = useMemo(() => {
    return categorias
      .map((categoria) => ({
        id: String(categoria.id),
        nombre: categoria.nombre || '-',
      }))
      .sort((a, b) => String(a.nombre).localeCompare(String(b.nombre), 'es', { sensitivity: 'base' }))
  }, [categorias])

  const filteredByCategory = useMemo(() => {
    if (categoryFilter === 'ALL') {
      return productos
    }
    if (categoryFilter === 'SIN_CATEGORIA') {
      return productos.filter((item) => !item?.categoria)
    }
    return productos.filter((item) => String(item?.categoria || '') === categoryFilter)
  }, [productos, categoryFilter])

  const openEditModal = (producto) => {
    setEditForm({
      id: producto.id,
      nombre: producto.nombre || '',
      descripcion: producto.descripcion || '',
      sku: producto.sku || '',
      tipo: producto.tipo || 'PRODUCTO',
      precio_referencia: producto.precio_referencia ?? 0,
      precio_costo: producto.precio_costo ?? 0,
      maneja_inventario: Boolean(producto.maneja_inventario),
      stock_actual: producto.stock_actual ?? 0,
      activo: Boolean(producto.activo),
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
    if (!editForm.id) {
      return
    }

    setSavingEdit(true)

    try {
      await api.patch(
        `/productos/${editForm.id}/`,
        {
          nombre: editForm.nombre,
          descripcion: editForm.descripcion,
          sku: editForm.sku,
          tipo: editForm.tipo,
          precio_referencia: Number(editForm.precio_referencia) || 0,
          precio_costo: Number(editForm.precio_costo) || 0,
          maneja_inventario: editForm.tipo === 'SERVICIO' ? false : Boolean(editForm.maneja_inventario),
          stock_actual: editForm.tipo === 'SERVICIO' ? 0 : Number(editForm.stock_actual) || 0,
          activo: Boolean(editForm.activo),
        },
        { suppressGlobalErrorToast: true },
      )

      invalidateProductosCatalogCache()
      toast.success('Producto actualizado correctamente.')
      closeEditModal()
      dispatch(fetchProductos({ includeInactive: canViewInactive && includeInactive }))
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo actualizar el producto.' }))
      setSavingEdit(false)
    }
  }

  const requestDeleteProducto = (producto) => {
    setProductoToDelete(producto)
  }

  const confirmDeleteProducto = async () => {
    const producto = productoToDelete
    if (!producto?.id) {
      return
    }

    setDeletingId(producto.id)

    try {
      await api.delete(`/productos/${producto.id}/`, { suppressGlobalErrorToast: true })
      invalidateProductosCatalogCache()
      toast.success('Producto procesado correctamente.')
      dispatch(fetchProductos({ includeInactive: canViewInactive && includeInactive }))
      setProductoToDelete(null)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo eliminar el producto.' }))
    } finally {
      setDeletingId(null)
    }
  }

  const columns = [
      columnHelper.accessor('creado_en', {
        header: 'Creado en',
        enableHiding: true,
      }),
      columnHelper.accessor('nombre', {
        header: 'Nombre',
        cell: (info) => info.getValue() || '-',
      }),
      columnHelper.accessor('sku', {
        header: 'SKU',
        cell: (info) => info.getValue() || '-',
      }),
      columnHelper.accessor('tipo', {
        header: 'Tipo',
        cell: (info) => info.getValue() || '-',
      }),
      columnHelper.accessor('categoria', {
        header: 'Categoria',
        cell: (info) => categoriaLabelById.get(String(info.getValue() || '')) || '-',
      }),
      columnHelper.accessor('precio_referencia', {
        header: 'Precio ref.',
        cell: (info) => formatMoney(info.getValue() ?? 0),
      }),
      columnHelper.accessor('stock_actual', {
        header: 'Stock actual',
        cell: (info) => formatSmartNumber(info.getValue() ?? 0, { maximumFractionDigits: 2 }),
      }),
      columnHelper.accessor('activo', {
        header: 'Activo',
        cell: (info) => (info.getValue() ? 'Si' : 'No'),
      }),
      columnHelper.display({
        id: 'acciones',
        header: 'Acciones',
        cell: (info) => {
          const producto = info.row.original

          return (
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => openEditModal(producto)}
                className="h-7 px-2 text-xs"
              >
                Editar
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={deletingId === producto.id}
                  onClick={() => requestDeleteProducto(producto)}
                className="h-7 border-destructive/40 px-2 text-xs text-destructive hover:bg-destructive/10"
              >
                {deletingId === producto.id ? 'Eliminando...' : 'Eliminar'}
              </Button>
            </div>
          )
        },
      }),
    ]

  const table = useReactTable({
    data: filteredByCategory,
    columns,
    initialState: {
      columnVisibility: { creado_en: false },
    },
    state: {
      sorting,
      globalFilter,
      pagination,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  const handleExportExcel = async () => {
    const rows = table.getSortedRowModel().rows

    if (rows.length === 0) {
      return
    }

    const today = getChileDateSuffix()

    await downloadExcelFile({
      sheetName: 'Productos',
      fileName: `productos_${today}.xlsx`,
      columns: [
        { header: 'Nombre', key: 'nombre', width: 30 },
        { header: 'SKU', key: 'sku', width: 20 },
        { header: 'Tipo', key: 'tipo', width: 18 },
        { header: 'Categoria', key: 'categoria', width: 22 },
        { header: 'Precio referencia', key: 'precio_referencia', width: 18 },
        { header: 'Precio costo', key: 'precio_costo', width: 18 },
        { header: 'Stock actual', key: 'stock_actual', width: 16 },
        { header: 'Activo', key: 'activo', width: 12 },
      ],
      rows: rows.map((row) => {
        const item = row.original
        return {
          nombre: item?.nombre || '',
          sku: item?.sku || '',
          tipo: item?.tipo || '',
          categoria: categoriaLabelById.get(String(item?.categoria || '')) || '-',
          precio_referencia: item?.precio_referencia ?? 0,
          precio_costo: item?.precio_costo ?? 0,
          stock_actual: item?.stock_actual ?? 0,
          activo: item?.activo ? 'Si' : 'No',
        }
      }),
    })
  }

  const handleExportPdf = async () => {
    const rows = table.getSortedRowModel().rows

    if (rows.length === 0) {
      return
    }

    const today = getChileDateSuffix()
    await downloadSimpleTablePdf({
      title: 'Listado de productos',
      fileName: `productos_${today}.pdf`,
      headers: ['Nombre', 'SKU', 'Tipo', 'Categoria', 'Precio ref.', 'Stock actual', 'Activo'],
      rows: rows.map((row) => {
        const item = row.original
        return [
          item?.nombre || '-',
          item?.sku || '-',
          item?.tipo || '-',
          categoriaLabelById.get(String(item?.categoria || '')) || '-',
          formatMoney(item?.precio_referencia ?? 0),
          Math.round(Number(item?.stock_actual ?? 0)).toLocaleString('es-CL'),
          item?.activo ? 'Si' : 'No',
        ]
      }),
    })
  }

  const getSortIndicator = (column) => {
    const sort = column.getIsSorted()

    if (sort === 'asc') {
      return '↑'
    }

    if (sort === 'desc') {
      return '↓'
    }

    return '↕'
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Productos</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          {canBulkImport ? (
            <BulkImportButton
              endpoint="/productos/bulk_import/"
              templateEndpoint="/productos/bulk_template/"
              onCompleted={() => {
                dispatch(fetchProductos({ includeInactive: canViewInactive && includeInactive }))
              }}
            />
          ) : null}
          <MenuButton
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
            disabled={status !== 'succeeded' || table.getRowModel().rows.length === 0}
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
          />
          <Link
            to="/productos/nuevo"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Nuevo producto
          </Link>
        </div>
      </div>

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="flex w-full flex-col gap-2 md:max-w-xl">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_220px]">
            <div className="relative w-full">
              <input
                type="text"
                value={globalFilter}
                onChange={(event) => setGlobalFilter(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') {
                    setGlobalFilter('')
                  }
                }}
                placeholder="Buscar por nombre, sku, tipo..."
                className="w-full rounded-md border border-input bg-background px-3 py-2 pr-9 text-sm"
              />
              {globalFilter ? (
                <button
                  type="button"
                  onClick={() => setGlobalFilter('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Limpiar busqueda"
                >
                  x
                </button>
              ) : null}
            </div>

            <div className="flex items-center gap-2 rounded-md border border-input bg-background px-2 py-1.5 text-sm">
              <label htmlFor="productos-categoria-filter" className="whitespace-nowrap text-muted-foreground">Categoria</label>
              <select
                id="productos-categoria-filter"
                className="w-full bg-transparent outline-none"
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value)}
              >
                <option value="ALL">Todas</option>
                <option value="SIN_CATEGORIA">Sin categoria</option>
                {categoryOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.nombre}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {canViewInactive ? (
            <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => setIncludeInactive(event.target.checked)}
              />
              Mostrar tambien productos no activos (solo admin)
            </label>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">
          Mostrando {table.getFilteredRowModel().rows.length} de {productos.length} productos
        </p>
      </div>

      {status === 'loading' && <p className="text-sm text-muted-foreground">Cargando productos...</p>}
      {status === 'failed' && <p className="text-sm text-destructive">{error}</p>}

      {status === 'succeeded' && (
        <div className="overflow-x-auto rounded-md border border-border bg-card">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className={
                        header.id === 'acciones'
                          ? 'w-px whitespace-nowrap px-2 py-2 text-left font-medium'
                          : 'px-3 py-2 text-left font-medium'
                      }
                    >
                      {header.isPlaceholder ? null : (
                        header.id === 'acciones' ? (
                          <span>{flexRender(header.column.columnDef.header, header.getContext())}</span>
                        ) : (
                          <button
                            type="button"
                            onClick={header.column.getToggleSortingHandler()}
                            className="inline-flex items-center gap-1 hover:text-primary"
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            <span className="text-xs text-muted-foreground">
                              {getSortIndicator(header.column)}
                            </span>
                          </button>
                        )
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={columns.length}>
                    No hay productos cargados.
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className="border-t border-border">
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className={
                          cell.column.id === 'acciones'
                            ? 'w-px whitespace-nowrap px-2 py-2'
                            : 'px-3 py-2'
                        }
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <TablePagination
        currentPage={table.getState().pagination.pageIndex + 1}
        totalPages={Math.max(1, table.getPageCount())}
        totalRows={table.getFilteredRowModel().rows.length}
        pageSize={table.getState().pagination.pageSize}
        onPrev={() => table.previousPage()}
        onNext={() => table.nextPage()}
      />

      {editModalOpen && (
        <div className="fixed inset-0 z-90 flex items-center justify-center bg-foreground/40 p-4">
          <div className="w-full max-w-2xl rounded-xl border border-border bg-card p-4 shadow-xl">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h3 className="text-lg font-semibold">Editar producto</h3>
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
                  SKU
                  <input
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.sku}
                    onChange={(event) => updateEditField('sku', event.target.value)}
                    required
                  />
                </label>

                <label className="text-sm md:col-span-2">
                  Descripcion
                  <textarea
                    rows={3}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.descripcion}
                    onChange={(event) => updateEditField('descripcion', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Tipo
                  <select
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.tipo}
                    onChange={(event) => {
                      const nextTipo = event.target.value
                      setEditForm((prev) => ({
                        ...prev,
                        tipo: nextTipo,
                        maneja_inventario: nextTipo === 'SERVICIO' ? false : true,
                        stock_actual: nextTipo === 'SERVICIO' ? 0 : prev.stock_actual,
                      }))
                    }}
                  >
                    <option value="PRODUCTO">Producto</option>
                    <option value="SERVICIO">Servicio</option>
                  </select>
                </label>

                <label className="text-sm">
                  Precio referencia
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.precio_referencia}
                    onChange={(event) => updateEditField('precio_referencia', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Precio costo
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2"
                    value={editForm.precio_costo}
                    onChange={(event) => updateEditField('precio_costo', event.target.value)}
                  />
                </label>

                <label className="text-sm">
                  Stock actual
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    disabled={editForm.tipo === 'SERVICIO'}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 disabled:opacity-60"
                    value={editForm.tipo === 'SERVICIO' ? 0 : editForm.stock_actual}
                    onChange={(event) => updateEditField('stock_actual', event.target.value)}
                  />
                </label>

                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={editForm.tipo === 'SERVICIO' ? false : editForm.maneja_inventario}
                    disabled={editForm.tipo === 'SERVICIO'}
                    onChange={(event) => updateEditField('maneja_inventario', event.target.checked)}
                  />
                  Maneja inventario
                </label>

                <label className="flex items-center gap-2 text-sm">
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
        open={Boolean(productoToDelete)}
        title="Eliminar producto"
        description={
          productoToDelete
            ? `Se procesara el producto "${productoToDelete.nombre}". Si tiene historial, quedara anulado en lugar de eliminarse.`
            : ''
        }
        confirmLabel="Confirmar"
        loading={deletingId === productoToDelete?.id}
        onCancel={() => {
          if (!deletingId) {
            setProductoToDelete(null)
          }
        }}
        onConfirm={confirmDeleteProducto}
      />
    </section>
  )
}

export default ProductosListPage
