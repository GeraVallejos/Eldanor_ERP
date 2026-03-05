import { useEffect, useMemo, useState } from 'react'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import {
  fetchProductos,
  selectProductos,
  selectProductosError,
  selectProductosStatus,
} from '@/modules/productos/productosSlice'

const columnHelper = createColumnHelper()

function ProductosListPage() {
  const dispatch = useDispatch()
  const productos = useSelector(selectProductos)
  const status = useSelector(selectProductosStatus)
  const error = useSelector(selectProductosError)
  const [sorting, setSorting] = useState([])
  const [globalFilter, setGlobalFilter] = useState('')

  useEffect(() => {
    if (status === 'idle') {
      dispatch(fetchProductos())
    }
  }, [dispatch, status])

  const columns = useMemo(
    () => [
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
      columnHelper.accessor('precio_referencia', {
        header: 'Precio ref.',
        cell: (info) => info.getValue() ?? 0,
      }),
      columnHelper.accessor('activo', {
        header: 'Activo',
        cell: (info) => (info.getValue() ? 'Si' : 'No'),
      }),
    ],
    [],
  )

  const table = useReactTable({
    data: productos,
    columns,
    state: {
      sorting,
      globalFilter,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const handleExportExcel = async () => {
    const rows = table.getRowModel().rows

    if (rows.length === 0) {
      return
    }

    const ExcelJS = await import('exceljs')
    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('Productos')

    sheet.columns = [
      { header: 'Nombre', key: 'nombre', width: 30 },
      { header: 'SKU', key: 'sku', width: 20 },
      { header: 'Tipo', key: 'tipo', width: 18 },
      { header: 'Precio referencia', key: 'precio_referencia', width: 18 },
      { header: 'Precio costo', key: 'precio_costo', width: 18 },
      { header: 'Stock actual', key: 'stock_actual', width: 16 },
      { header: 'Activo', key: 'activo', width: 12 },
    ]

    rows.forEach((row) => {
      const item = row.original
      sheet.addRow({
        nombre: item?.nombre || '',
        sku: item?.sku || '',
        tipo: item?.tipo || '',
        precio_referencia: item?.precio_referencia ?? 0,
        precio_costo: item?.precio_costo ?? 0,
        stock_actual: item?.stock_actual ?? 0,
        activo: item?.activo ? 'Si' : 'No',
      })
    })

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    const today = new Date().toISOString().slice(0, 10)

    link.href = url
    link.download = `productos_${today}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Productos</h2>
          <p className="text-sm text-muted-foreground">Listado de productos por empresa activa.</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => dispatch(fetchProductos())}
            className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
          >
            Recargar
          </button>
          <button
            type="button"
            onClick={handleExportExcel}
            disabled={status !== 'succeeded' || table.getRowModel().rows.length === 0}
            className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
          >
            Exportar Excel
          </button>
          <Link
            to="/productos/nuevo"
            className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
          >
            Nuevo producto
          </Link>
        </div>
      </div>

      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <input
          type="text"
          value={globalFilter}
          onChange={(event) => setGlobalFilter(event.target.value)}
          placeholder="Buscar por nombre, sku, tipo..."
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm md:max-w-sm"
        />
        <p className="text-xs text-muted-foreground">
          Mostrando {table.getRowModel().rows.length} de {productos.length} productos
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
                    <th key={header.id} className="px-3 py-2 text-left font-medium">
                      {header.isPlaceholder ? null : (
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
                      <td key={cell.id} className="px-3 py-2">
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
    </section>
  )
}

export default ProductosListPage
