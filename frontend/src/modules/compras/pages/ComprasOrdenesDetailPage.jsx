import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import MenuButton from '@/components/ui/MenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
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

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function canCrearDocumento(orden, permissions) {
  return permissions['COMPRAS.CREAR'] && ['BORRADOR', 'ENVIADA', 'PARCIAL'].includes(String(orden?.estado))
}

function canEditarOrden(orden, permissions) {
  return permissions['COMPRAS.EDITAR'] && orden?.estado === 'BORRADOR'
}

function canEnviarOrden(orden, permissions) {
  return permissions['COMPRAS.APROBAR'] && orden?.estado === 'BORRADOR'
}

function ComprasOrdenesDetailPage() {
  const { id: ordenId } = useParams()
  const permissions = usePermissions(['COMPRAS.CREAR', 'COMPRAS.EDITAR', 'COMPRAS.APROBAR'])
  const [status, setStatus] = useState('idle')
  const [orden, setOrden] = useState(null)
  const [items, setItems] = useState([])
  const [documentosAsociados, setDocumentosAsociados] = useState([])
  const [recepcionesAsociadas, setRecepcionesAsociadas] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [impuestos, setImpuestos] = useState([])
  const [updatingEstado, setUpdatingEstado] = useState(false)

  const loadData = useCallback(async () => {
    setStatus('loading')
    try {
      const [{ data: ordenData }, { data: itemsData }, { data: documentosData }, { data: recepcionesData }, { data: proveedoresData }, { data: contactosData }, { data: impuestosData }] =
        await Promise.all([
          api.get(`/ordenes-compra/${ordenId}/`, { suppressGlobalErrorToast: true }),
          api.get('/ordenes-compra-items/', { suppressGlobalErrorToast: true }),
          api.get('/documentos-compra/', { suppressGlobalErrorToast: true }),
          api.get('/recepciones-compra/', { suppressGlobalErrorToast: true }),
          api.get('/proveedores/', { suppressGlobalErrorToast: true }),
          api.get('/contactos/', { suppressGlobalErrorToast: true }),
          api.get('/impuestos/', { suppressGlobalErrorToast: true }),
        ])

      setOrden(ordenData)
      setItems(normalizeListResponse(itemsData).filter((row) => String(row.orden_compra) === String(ordenId)))
      setDocumentosAsociados(
        normalizeListResponse(documentosData).filter((doc) => String(doc.orden_compra) === String(ordenId)),
      )
      setRecepcionesAsociadas(
        normalizeListResponse(recepcionesData).filter((rec) => String(rec.orden_compra) === String(ordenId)),
      )
      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
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

  const impuestoById = useMemo(() => {
    const map = new Map()
    impuestos.forEach((impuesto) => {
      map.set(String(impuesto.id), impuesto)
    })
    return map
  }, [impuestos])

  const proveedor = proveedorById.get(String(orden?.proveedor))
  const contacto = contactoById.get(String(proveedor?.contacto))

  const getTodaySuffix = () => getChileDateSuffix()

  const totalSubtotal = useMemo(() => {
    // Totales de la cabecera (calculados por el backend al guardar items)
    return Number(orden?.subtotal ?? 0)
  }, [orden])

  const totalImpuesto = useMemo(() => {
    return Number(orden?.impuestos ?? 0)
  }, [orden])

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
                fecha_emision: formatDateChile(orden.fecha_emision),
                fecha_entrega: formatDateChile(orden.fecha_entrega),
                producto: item.producto_nombre || item.descripcion || '-',
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
                fecha_emision: formatDateChile(orden.fecha_emision),
                fecha_entrega: formatDateChile(orden.fecha_entrega),
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
                item.producto_nombre || item.descripcion || '-',
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
          <p className="text-sm text-muted-foreground">Estado: <span className="font-medium">{orden.estado}</span></p>
        </div>

        <div className="flex gap-2">
          <MenuButton
            variant="outline"
            size="md"
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
          />
          {canEnviarOrden(orden, permissions) ? (
            <Button
              variant="default"
              size="md"
              disabled={updatingEstado}
              onClick={async () => {
                setUpdatingEstado(true)
                try {
                  const { data } = await api.post(`/ordenes-compra/${ordenId}/enviar/`, {}, { suppressGlobalErrorToast: true })
                  setOrden((prev) => ({ ...prev, ...data }))
                  toast.success('Orden enviada correctamente.')
                } catch (error) {
                  toast.error(normalizeApiError(error, { fallback: 'No se pudo enviar la orden.' }))
                } finally {
                  setUpdatingEstado(false)
                }
              }}
            >
              {updatingEstado ? 'Enviando...' : 'Enviar orden'}
            </Button>
          ) : null}
          {canCrearDocumento(orden, permissions) ? (
            <Link
              to={`/compras/documentos/nuevo?orden_compra=${orden.id}`}
              className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
            >
              Crear documento
            </Link>
          ) : null}
          {canEditarOrden(orden, permissions) ? (
            <Link
              to={`/compras/ordenes/${orden.id}/editar`}
              className={cn(buttonVariants({ variant: 'default', size: 'md' }))}
            >
              Editar
            </Link>
          ) : null}
          <Link
            to="/compras/ordenes"
            className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
          >
            Volver
          </Link>
          <Link
            to={`/compras/ordenes/${orden.id}/trazabilidad`}
            className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}
          >
            Seguimiento
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
          <p className="mt-1 text-sm">{formatDateChile(orden.fecha_emision)}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Fecha de entrega</p>
          <p className="mt-1 text-sm">{formatDateChile(orden.fecha_entrega)}</p>
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

      <div className="rounded-md border border-border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">Documentos asociados</p>
        {documentosAsociados.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Esta orden no tiene documentos asociados.</p>
        ) : (
          <div className="mt-2 flex flex-col gap-2">
            {documentosAsociados.map((doc) => (
              <Link
                key={doc.id}
                to={`/compras/documentos/${doc.id}`}
                className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
              >
                <span>
                  {doc.tipo_documento === 'FACTURA_COMPRA'
                    ? 'Factura'
                    : doc.tipo_documento === 'BOLETA_COMPRA'
                    ? 'Boleta'
                    : 'Guía'}
                </span>
                <span>
                  {doc.serie ? `${doc.serie}-` : ''}
                  {doc.folio || 'S/F'}
                </span>
                <span className="text-muted-foreground">({doc.estado || '-'})</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-md border border-border bg-card p-4">
        <p className="text-xs font-medium text-muted-foreground">Recepciones de compra</p>
        {recepcionesAsociadas.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">Esta orden no tiene recepciones registradas.</p>
        ) : (
          <div className="mt-2 flex flex-col gap-2">
            {recepcionesAsociadas.map((rec) => (
              <Link
                key={rec.id}
                to={`/compras/recepciones/${rec.id}/editar`}
                className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
              >
                <span>Recepcion {rec.fecha}</span>
                <span className="text-muted-foreground">({rec.estado})</span>
              </Link>
            ))}
          </div>
        )}
      </div>

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

                return (
                  <tr key={index} className="border-t border-border">
                    <td className="px-3 py-2">{item.producto_nombre || item.descripcion || '-'}</td>
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
