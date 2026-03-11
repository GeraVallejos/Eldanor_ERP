import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import { getProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

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

function ComprasOrdenesDetailPage() {
  const { id: ordenId } = useParams()
  const [status, setStatus] = useState('idle')
  const [orden, setOrden] = useState(null)
  const [items, setItems] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [productos, setProductos] = useState([])
  const [impuestos, setImpuestos] = useState([])

  const loadData = useCallback(async () => {
    setStatus('loading')
    try {
      const [{ data: ordenData }, { data: itemsData }, { data: proveedoresData }, { data: contactosData }, productosData, { data: impuestosData }] =
        await Promise.all([
          api.get(`/ordenes-compra/${ordenId}/`, { suppressGlobalErrorToast: true }),
          api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true }),
          api.get('/proveedores/', { suppressGlobalErrorToast: true }),
          api.get('/contactos/', { suppressGlobalErrorToast: true }),
          getProductosCatalog(),
          api.get('/impuestos/', { suppressGlobalErrorToast: true }),
        ])

      setOrden(ordenData)
      setItems(normalizeListResponse(itemsData).filter((row) => String(row.orden_compra) === String(ordenId)))
      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setProductos(productosData)
      setImpuestos(normalizeListResponse(impuestosData))
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar la orden de compra.' }))
    }
  }, [ordenId])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [loadData])

  const proveedorById = useMemo(() => {
    const map = new Map()
    proveedores.forEach((proveedor) => {
      map.set(String(proveedor.id), proveedor)
    })
    return map
  }, [proveedores])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((contacto) => {
      map.set(String(contacto.id), contacto)
    })
    return map
  }, [contactos])

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

  const proveedor = proveedorById.get(String(orden?.proveedor))
  const contacto = contactoById.get(String(proveedor?.contacto))

  const getTodaySuffix = () => new Date().toISOString().slice(0, 10)

  const totalSubtotal = useMemo(() => {
    return items.reduce((sum, item) => {
      const cantidad = Number(item.cantidad ?? 0)
      const precio_unitario = Number(item.precio_unitario ?? 0)
      return sum + cantidad * precio_unitario
    }, 0)
  }, [items])

  const totalImpuesto = useMemo(() => {
    return items.reduce((sum, item) => {
      const cantidad = Number(item.cantidad ?? 0)
      const precio_unitario = Number(item.precio_unitario ?? 0)
      const impuesto = impuestoById.get(String(item.impuesto))
      const porcentaje = Number(impuesto?.porcentaje ?? 0)
      return sum + cantidad * precio_unitario * (porcentaje / 100)
    }, 0)
  }, [items, impuestoById])

  const handleExportExcel = async () => {
    if (!orden) return

    await downloadExcelFile({
      sheetName: 'DetalleOrdenCompra',
      fileName: `orden_compra_${orden.numero || orden.id}_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: 'Numero OC', key: 'numero_oc', width: 16 },
        { header: 'Estado', key: 'estado', width: 16 },
        { header: 'Proveedor', key: 'proveedor', width: 30 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 16 },
        { header: 'Fecha entrega', key: 'fecha_entrega', width: 16 },
        { header: 'Producto', key: 'producto', width: 30 },
        { header: 'Descripcion', key: 'descripcion', width: 40 },
        { header: 'Cantidad', key: 'cantidad', width: 12 },
        { header: 'Precio unitario', key: 'precio_unitario', width: 16 },
        { header: 'Subtotal', key: 'subtotal', width: 16 },
        { header: 'Impuesto %', key: 'impuesto_porcentaje', width: 12 },
        { header: 'Total', key: 'total', width: 16 },
      ],
      rows:
        items.length > 0
          ? items.map((item) => {
              const cantidad = Number(item.cantidad ?? 0)
              const precioUnitario = Number(item.precio_unitario ?? 0)
              const impuesto = impuestoById.get(String(item.impuesto))
              const porcentaje = Number(impuesto?.porcentaje ?? 0)
              const subtotal = cantidad * precioUnitario
              const total = subtotal + subtotal * (porcentaje / 100)

              return {
                numero_oc: orden.numero || '-',
                estado: orden.estado || '-',
                proveedor: contacto?.nombre || '-',
                fecha_emision: orden.fecha_emision || '-',
                fecha_entrega: orden.fecha_entrega || '-',
                producto: productoById.get(String(item.producto))?.nombre || '-',
                descripcion: item.descripcion || '-',
                cantidad,
                precio_unitario: precioUnitario,
                subtotal,
                impuesto_porcentaje: porcentaje,
                total,
              }
            })
          : [
              {
                numero_oc: orden.numero || '-',
                estado: orden.estado || '-',
                proveedor: contacto?.nombre || '-',
                fecha_emision: orden.fecha_emision || '-',
                fecha_entrega: orden.fecha_entrega || '-',
                producto: '-',
                descripcion: '-',
                cantidad: 0,
                precio_unitario: 0,
                subtotal: 0,
                impuesto_porcentaje: 0,
                total: 0,
              },
            ],
    })
  }

  const handleExportPdf = async () => {
    if (!orden) return

    await downloadSimpleTablePdf({
      title: `Detalle OC #${orden.numero || orden.id}`,
      fileName: `orden_compra_${orden.numero || orden.id}_${getTodaySuffix()}.pdf`,
      headers: ['Numero OC', 'Estado', 'Proveedor', 'Producto', 'Cantidad', 'Precio unit.', 'Impuesto %', 'Total'],
      rows:
        items.length > 0
          ? items.map((item) => {
              const cantidad = Number(item.cantidad ?? 0)
              const precioUnitario = Number(item.precio_unitario ?? 0)
              const impuesto = impuestoById.get(String(item.impuesto))
              const porcentaje = Number(impuesto?.porcentaje ?? 0)
              const subtotal = cantidad * precioUnitario
              const total = subtotal + subtotal * (porcentaje / 100)

              return [
                String(orden.numero || '-'),
                String(orden.estado || '-'),
                contacto?.nombre || '-',
                productoById.get(String(item.producto))?.nombre || '-',
                String(cantidad),
                formatMoney(precioUnitario),
                `${porcentaje}%`,
                formatMoney(total),
              ]
            })
          : [[String(orden.numero || '-'), String(orden.estado || '-'), contacto?.nombre || '-', '-', '0', '0', '0%', '0']],
    })
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando orden...</p>
  }

  if (status === 'failed' || !orden) {
    return <p className="text-sm text-destructive">No se pudo cargar la orden de compra.</p>
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Orden de compra #{orden.numero}</h2>
          <p className="text-sm text-muted-foreground">Estado: {orden.estado}</p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="md" onClick={handleExportExcel}>
            Exportar Excel
          </Button>
          <Button variant="outline" size="md" onClick={handleExportPdf}>
            Exportar PDF
          </Button>
          {orden.estado === 'BORRADOR' && (
            <Link
              to={`/compras/documentos/nuevo?orden_compra=${orden.id}`}
              className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
            >
              Crear documento
            </Link>
          )}
          {orden.estado === 'BORRADOR' && (
            <Link
              to={`/compras/ordenes/${orden.id}/editar`}
              className={cn(buttonVariants({ variant: 'default', size: 'md' }))}
            >
              Editar
            </Link>
          )}
          <Link
            to="/compras/ordenes"
            className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
          >
            Volver
          </Link>
        </div>
      </div>

      <div className="grid gap-4 rounded-md border border-border bg-card p-4 md:grid-cols-2">
        <div>
          <p className="text-xs font-medium text-muted-foreground">Proveedor</p>
          <p className="mt-1 text-sm">{contacto?.nombre || '-'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Fecha de emisión</p>
          <p className="mt-1 text-sm">{orden.fecha_emision || '-'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Fecha de entrega</p>
          <p className="mt-1 text-sm">{orden.fecha_entrega || '-'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">RUT Proveedor</p>
          <p className="mt-1 text-sm">{contacto?.rut || '-'}</p>
        </div>
      </div>

      {orden.observaciones && (
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs font-medium text-muted-foreground">Observaciones</p>
          <p className="mt-2 text-sm whitespace-pre-wrap">{orden.observaciones}</p>
        </div>
      )}

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Producto</th>
              <th className="px-3 py-2 text-left font-medium">Descripción</th>
              <th className="px-3 py-2 text-right font-medium">Cantidad</th>
              <th className="px-3 py-2 text-right font-medium">Precio unitario</th>
              <th className="px-3 py-2 text-right font-medium">Subtotal</th>
              <th className="px-3 py-2 text-right font-medium">Impuesto %</th>
              <th className="px-3 py-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={7}>
                  Sin items
                </td>
              </tr>
            ) : (
              items.map((item, index) => {
                const cantidad = Number(item.cantidad ?? 0)
                const precio_unitario = Number(item.precio_unitario ?? 0)
                const impuesto = impuestoById.get(String(item.impuesto))
                const porcentaje = Number(impuesto?.porcentaje ?? 0)
                const subtotal = cantidad * precio_unitario
                const total = subtotal + subtotal * (porcentaje / 100)
                const producto = productoById.get(String(item.producto))

                return (
                  <tr key={index} className="border-t border-border">
                    <td className="px-3 py-2">{producto?.nombre || '-'}</td>
                    <td className="px-3 py-2">{item.descripcion || '-'}</td>
                    <td className="px-3 py-2 text-right">{cantidad}</td>
                    <td className="px-3 py-2 text-right">{formatMoney(precio_unitario)}</td>
                    <td className="px-3 py-2 text-right">{formatMoney(subtotal)}</td>
                    <td className="px-3 py-2 text-right">{porcentaje}%</td>
                    <td className="px-3 py-2 text-right">{formatMoney(total)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-border bg-card p-4 md:flex-row md:justify-end md:gap-8">
        <div>
          <p className="text-xs text-muted-foreground">Subtotal</p>
          <p className="text-xl font-semibold">{formatMoney(totalSubtotal)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Impuestos</p>
          <p className="text-xl font-semibold">{formatMoney(totalImpuesto)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Total</p>
          <p className="text-2xl font-bold">{formatMoney(totalSubtotal + totalImpuesto)}</p>
        </div>
      </div>
    </section>
  )
}

export default ComprasOrdenesDetailPage
