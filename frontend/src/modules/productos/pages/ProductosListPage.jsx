import { useEffect, useMemo, useState } from 'react'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import ActiveSearchFilter from '@/components/ui/ActiveSearchFilter'
import Button from '@/components/ui/Button'
import BulkImportButton from '@/components/ui/BulkImportButton'
import MenuButton from '@/components/ui/MenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import TablePagination from '@/components/ui/TablePagination'
import { getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP, formatSmartNumber } from '@/lib/numberFormat'
import { useResponsiveTablePageSize } from '@/lib/useResponsiveTablePageSize'
import { cn } from '@/lib/utils'
import { productosApi } from '@/modules/productos/store/api'
import { useProductosListado } from '@/modules/productos/store/hooks'
import { useDeleteProductoAction } from '@/modules/productos/store/mutations'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import { hasAnyRole } from '@/modules/shared/auth/roles'
import { usePermissions } from '@/modules/shared/auth/usePermission'

const columnHelper = createColumnHelper()

const tipoFilterOptions = [
  { value: 'PRODUCTO', label: 'Productos' },
  { value: 'SERVICIO', label: 'Servicios' },
  { value: 'ALL', label: 'Todos' },
]

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function getTipoFilterLabel(tipoFilter) {
  if (tipoFilter === 'SERVICIO') {
    return 'servicios'
  }

  if (tipoFilter === 'ALL') {
    return 'registros'
  }

  return 'productos'
}

function sortProductosForExport(productos, sorting, categoriaLabelById) {
  const rows = Array.isArray(productos) ? [...productos] : []
  const activeSort = Array.isArray(sorting) ? sorting[0] : null
  if (!activeSort?.id) {
    return rows
  }

  const direction = activeSort.desc ? -1 : 1
  const resolveValue = (item) => {
    if (activeSort.id === 'categoria') {
      return categoriaLabelById.get(String(item?.categoria || '')) || '-'
    }
    return item?.[activeSort.id]
  }

  rows.sort((left, right) => {
    const leftValue = resolveValue(left)
    const rightValue = resolveValue(right)

    if (leftValue == null && rightValue == null) return 0
    if (leftValue == null) return 1
    if (rightValue == null) return -1

    if (typeof leftValue === 'number' && typeof rightValue === 'number') {
      return (leftValue - rightValue) * direction
    }

    return String(leftValue).localeCompare(String(rightValue), 'es', { sensitivity: 'base', numeric: true }) * direction
  })

  return rows
}

function ProductosListPage() {
  const responsivePageSize = useResponsiveTablePageSize({ mobileRows: 20, reservedHeight: 470, desktopMaxRows: 14 })
  const currentUser = useSelector(selectCurrentUser)
  const permissions = usePermissions(['PRODUCTOS.CREAR', 'PRODUCTOS.EDITAR', 'PRODUCTOS.BORRAR'])
  const [sorting, setSorting] = useState([{ id: 'creado_en', desc: true }])
  const [globalFilter, setGlobalFilter] = useState('')
  const [tipoFilter, setTipoFilter] = useState('PRODUCTO')
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: responsivePageSize })
  const [productoToDelete, setProductoToDelete] = useState(null)
  const [includeInactive, setIncludeInactive] = useState(false)

  const canViewInactive = hasAnyRole(currentUser, ['OWNER', 'ADMIN'])
  const canBulkImport = permissions['PRODUCTOS.CREAR'] && hasAnyRole(currentUser, ['ADMIN'])
  const canCreate = permissions['PRODUCTOS.CREAR']
  const canEdit = permissions['PRODUCTOS.EDITAR']
  const canDelete = permissions['PRODUCTOS.BORRAR']
  const {
    productos,
    totalCount,
    status,
    error,
    categorias,
    reload,
  } = useProductosListado({
    includeInactive: canViewInactive && includeInactive,
    query: globalFilter,
    tipo: tipoFilter,
    categoria: categoryFilter,
    page: pagination.pageIndex + 1,
    pageSize: pagination.pageSize,
  })
  const { deletingId, deleteProducto } = useDeleteProductoAction({
    canDelete,
    onSuccess: async () => {
      setProductoToDelete(null)
      await reload()
    },
  })

  useEffect(() => {
    setPagination((prev) => (
      prev.pageIndex === 0
        ? prev
        : { ...prev, pageIndex: 0 }
    ))
  }, [globalFilter, tipoFilter, categoryFilter, includeInactive])

  useEffect(() => {
    setPagination((prev) => (
      prev.pageSize === responsivePageSize
        ? prev
        : { ...prev, pageIndex: 0, pageSize: responsivePageSize }
    ))
  }, [responsivePageSize])

  useEffect(() => {
    setPagination((prev) => {
      const totalPages = Math.max(1, Math.ceil(totalCount / prev.pageSize))
      const maxPageIndex = Math.max(0, totalPages - 1)
      if (prev.pageIndex <= maxPageIndex) {
        return prev
      }
      return { ...prev, pageIndex: maxPageIndex }
    })
  }, [totalCount])

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

  const requestDeleteProducto = (producto) => {
    setProductoToDelete(producto)
  }

  const buildProductosQueryParams = (overrides = {}) => {
    const params = {
      includeInactive: canViewInactive && includeInactive,
      query: globalFilter,
      tipo: tipoFilter,
      categoria: categoryFilter,
      page: pagination.pageIndex + 1,
      pageSize: pagination.pageSize,
      ...overrides,
    }

    if (!params.query) delete params.query
    if (!params.tipo || params.tipo === 'ALL') delete params.tipo
    if (!params.categoria || params.categoria === 'ALL') delete params.categoria

    return params
  }

  const fetchAllFilteredProductos = async () => {
    const pageSize = 100
    const allRows = []
    let currentPage = 1
    let totalPages = 1

    while (currentPage <= totalPages) {
      const requestOptions = buildProductosQueryParams({ page: currentPage, pageSize })
      const params = {
        page: requestOptions.page,
        page_size: requestOptions.pageSize,
      }
      if (requestOptions.includeInactive) params.include_inactive = 1
      if (requestOptions.query) params.q = requestOptions.query
      if (requestOptions.tipo) params.tipo = requestOptions.tipo
      if (requestOptions.categoria) params.categoria = requestOptions.categoria

      const data = await productosApi.getListWithCount(productosApi.endpoints.productos, params)
      const results = data.results
      const count = data.count
      totalPages = Math.max(1, Math.ceil(count / pageSize))
      allRows.push(...results)
      currentPage += 1
    }

    return sortProductosForExport(allRows, sorting, categoriaLabelById)
  }

  const confirmDeleteProducto = async () => {
    const producto = productoToDelete
    if (!producto?.id) {
      return
    }
    await deleteProducto(producto)
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
              <Link
                to={`/productos/${producto.id}`}
                className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-7 px-2 text-xs')}
              >
                Ver
              </Link>
              {canEdit ? (
                <Link
                  to={`/productos/${producto.id}/editar`}
                  className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'h-7 px-2 text-xs')}
                >
                  Editar
                </Link>
              ) : null}
              {canDelete ? (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={deletingId === producto.id}
                  onClick={() => requestDeleteProducto(producto)}
                  className="h-7 border-destructive/40 px-2 text-xs text-destructive hover:bg-destructive/10"
                >
                  {deletingId === producto.id ? 'Eliminando...' : 'Eliminar'}
                </Button>
              ) : null}
            </div>
          )
        },
      }),
    ]

  // TanStack Table expone callbacks no compatibles con la regla del React Compiler.
  // Aqui se usa de forma local y no se propaga a hooks memoizados.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: productos,
    columns,
    initialState: {
      columnVisibility: { creado_en: false },
    },
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const handleExportExcel = async () => {
    if (totalCount === 0) {
      return
    }

    const today = getChileDateSuffix()
    const rows = await fetchAllFilteredProductos()

    await downloadExcelFile({
      sheetName: 'Productos',
      fileName: `productos_${today}.xlsx`,
      columns: [
        { header: 'Nombre', key: 'nombre', width: 30 },
        { header: 'SKU', key: 'sku', width: 20 },
        { header: 'Tipo', key: 'tipo', width: 18 },
        { header: 'Categoria', key: 'categoria', width: 22 },
        { header: 'Precio referencia', key: 'precio_referencia', width: 18, numFmt: '#,##0.##' },
        { header: 'Precio costo', key: 'precio_costo', width: 18, numFmt: '#,##0.##' },
        { header: 'Stock actual', key: 'stock_actual', width: 16, numFmt: '#,##0.##' },
        { header: 'Activo', key: 'activo', width: 12 },
      ],
      rows: rows.map((item) => {
        return {
          nombre: item?.nombre || '',
          sku: item?.sku || '',
          tipo: item?.tipo || '',
          categoria: categoriaLabelById.get(String(item?.categoria || '')) || '-',
          precio_referencia: Number(item?.precio_referencia ?? 0),
          precio_costo: Number(item?.precio_costo ?? 0),
          stock_actual: Number(item?.stock_actual ?? 0),
          activo: item?.activo ? 'Si' : 'No',
        }
      }),
    })
  }

  const handleExportPdf = async () => {
    if (totalCount === 0) {
      return
    }

    const today = getChileDateSuffix()
    const rows = await fetchAllFilteredProductos()
    await downloadSimpleTablePdf({
      title: 'Listado de productos',
      fileName: `productos_${today}.pdf`,
      headers: ['Nombre', 'SKU', 'Tipo', 'Categoria', 'Precio ref.', 'Stock actual', 'Activo'],
      rows: rows.map((item) => {
        return [
          item?.nombre || '-',
          item?.sku || '-',
          item?.tipo || '-',
          categoriaLabelById.get(String(item?.categoria || '')) || '-',
          formatMoney(item?.precio_referencia ?? 0),
          formatSmartNumber(item?.stock_actual ?? 0, { maximumFractionDigits: 2 }),
          item?.activo ? 'Si' : 'No',
        ]
      }),
    })
  }

  const getSortIndicator = (column) => {
    const sort = column.getIsSorted()

    if (sort === 'asc') {
      return 'Asc'
    }

    if (sort === 'desc') {
      return 'Desc'
    }

    return 'Ord'
  }

  const tipoFilterLabel = getTipoFilterLabel(tipoFilter)

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-2xl font-semibold">Productos</h2>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          {canBulkImport ? (
            <BulkImportButton
              endpoint="/productos/bulk_import/"
              templateEndpoint="/productos/bulk_template/"
              previewBeforeImport
              previewTitle="Confirmar carga masiva de productos"
              onCompleted={() => {
                void reload()
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
          {canCreate ? (
            <Link
              to="/productos/nuevo"
              className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
            >
              Nuevo producto
            </Link>
          ) : null}
        </div>
      </div>

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="flex w-full flex-col gap-2 md:max-w-xl">
          <div className="flex flex-wrap gap-2">
            {tipoFilterOptions.map((option) => {
              const selected = tipoFilter === option.value
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setTipoFilter(option.value)}
                  aria-pressed={selected}
                  className={cn(
                    'rounded-md border px-3 py-1.5 text-sm transition-colors',
                    selected
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-input bg-background text-foreground hover:bg-muted',
                  )}
                >
                  {option.label}
                </button>
              )
            })}
          </div>

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
          <ActiveSearchFilter
            query={globalFilter}
            filteredCount={productos.length}
            totalCount={totalCount}
            noun={tipoFilterLabel}
            onClear={() => setGlobalFilter('')}
          />
          {canViewInactive ? (
            <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
              <input
                id="productos-include-inactive"
                type="checkbox"
                checked={includeInactive}
                onChange={(event) => setIncludeInactive(event.target.checked)}
              />
              <label htmlFor="productos-include-inactive" className="cursor-pointer">
                Mostrar tambien productos no activos (solo admin)
              </label>
            </div>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">
          Mostrando {productos.length} de {totalCount} {tipoFilterLabel}
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
                    No hay {tipoFilterLabel} cargados.
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
        currentPage={pagination.pageIndex + 1}
        totalPages={Math.max(1, Math.ceil(totalCount / pagination.pageSize))}
        totalRows={totalCount}
        pageSize={pagination.pageSize}
        onPrev={() => setPagination((prev) => ({ ...prev, pageIndex: Math.max(0, prev.pageIndex - 1) }))}
        onNext={() => setPagination((prev) => ({
          ...prev,
          pageIndex: Math.min(Math.max(0, Math.ceil(totalCount / prev.pageSize) - 1), prev.pageIndex + 1),
        }))}
      />

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
