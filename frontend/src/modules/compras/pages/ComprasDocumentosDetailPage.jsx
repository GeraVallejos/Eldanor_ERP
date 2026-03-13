import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import ExportMenuButton from '@/components/ui/ExportMenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { getProductosCatalog } from '@/modules/productos/services/productosCatalogCache'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'

const TIPO_LABELS = {
  GUIA_RECEPCION: 'Guia de recepcion',
  FACTURA_COMPRA: 'Factura de compra',
  BOLETA_COMPRA: 'Boleta de compra',
}

const ESTADO_LABELS = {
  BORRADOR: 'Borrador',
  CONFIRMADO: 'Confirmado',
  ANULADO: 'Anulado',
}

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function ComprasDocumentosDetailPage() {
  const { id } = useParams()
  const [status, setStatus] = useState('idle')
  const [documento, setDocumento] = useState(null)
  const [items, setItems] = useState([])
  const [proveedores, setProveedores] = useState([])
  const [contactos, setContactos] = useState([])
  const [productos, setProductos] = useState([])

  const loadData = useCallback(async () => {
    setStatus('loading')
    try {
      const [{ data: documentoData }, { data: itemsData }, { data: proveedoresData }, { data: contactosData }, productosData] = await Promise.all([
        api.get(`/documentos-compra/${id}/`, { suppressGlobalErrorToast: true }),
        api.get(`/documentos-compra-items/?documento=${id}`, { suppressGlobalErrorToast: true }),
        api.get('/proveedores/', { suppressGlobalErrorToast: true }),
        api.get('/contactos/', { suppressGlobalErrorToast: true }),
        getProductosCatalog(),
      ])

      setDocumento(documentoData)
      setItems(normalizeListResponse(itemsData))
      setProveedores(normalizeListResponse(proveedoresData))
      setContactos(normalizeListResponse(contactosData))
      setProductos(productosData)
      setStatus('succeeded')
    } catch (error) {
      setStatus('failed')
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el detalle del documento.' }))
    }
  }, [id])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [loadData])

  const proveedorById = useMemo(() => {
    const map = new Map()
    proveedores.forEach((p) => map.set(String(p.id), p))
    return map
  }, [proveedores])

  const contactoById = useMemo(() => {
    const map = new Map()
    contactos.forEach((c) => map.set(String(c.id), c))
    return map
  }, [contactos])

  const productoById = useMemo(() => {
    const map = new Map()
    productos.forEach((p) => map.set(String(p.id), p))
    return map
  }, [productos])

  const proveedor = proveedorById.get(String(documento?.proveedor || ''))
  const contacto = contactoById.get(String(proveedor?.contacto || ''))

  const getTodaySuffix = () => getChileDateSuffix()

  const handleExportExcel = async () => {
    if (!documento) return

    await downloadExcelFile({
      sheetName: 'DetalleDocumentoCompra',
      fileName: `documento_compra_${documento.folio || documento.id}_${getTodaySuffix()}.xlsx`,
      columns: [
        { header: 'Tipo', key: 'tipo', width: 20 },
        { header: 'Folio', key: 'folio', width: 18 },
        { header: 'Proveedor', key: 'proveedor', width: 30 },
        { header: 'Estado', key: 'estado', width: 16 },
        { header: 'Fecha emision', key: 'fecha_emision', width: 16 },
        { header: 'Producto', key: 'producto', width: 30 },
        { header: 'Cantidad', key: 'cantidad', width: 14 },
        { header: 'Precio unitario', key: 'precio_unitario', width: 16 },
        { header: 'Descuento', key: 'descuento', width: 12 },
        { header: 'Subtotal', key: 'subtotal', width: 16 },
      ],
      rows:
        items.length > 0
          ? items.map((item) => ({
              tipo: TIPO_LABELS[documento.tipo_documento] || documento.tipo_documento,
              folio: documento.folio || '-',
              proveedor: contacto?.nombre || '-',
              estado: ESTADO_LABELS[documento.estado] || documento.estado,
              fecha_emision: formatDateChile(documento.fecha_emision),
              producto: productoById.get(String(item.producto))?.nombre || item.descripcion || '-',
              cantidad: Number(item.cantidad || 0),
              precio_unitario: Number(item.precio_unitario || 0),
              descuento: Number(item.descuento || 0),
              subtotal: Number(item.subtotal || 0),
            }))
          : [
              {
                tipo: TIPO_LABELS[documento.tipo_documento] || documento.tipo_documento,
                folio: documento.folio || '-',
                proveedor: contacto?.nombre || '-',
                estado: ESTADO_LABELS[documento.estado] || documento.estado,
                fecha_emision: formatDateChile(documento.fecha_emision),
                producto: '-',
                cantidad: 0,
                precio_unitario: 0,
                descuento: 0,
                subtotal: 0,
              },
            ],
    })
  }

  const handleExportPdf = async () => {
    if (!documento) return

    const itemRows =
      items.length > 0
        ? items.map((item) => [
            TIPO_LABELS[documento.tipo_documento] || documento.tipo_documento,
            documento.folio || '-',
            contacto?.nombre || '-',
            ESTADO_LABELS[documento.estado] || documento.estado,
            formatDateChile(documento.fecha_emision),
            productoById.get(String(item.producto))?.nombre || item.descripcion || '-',
            String(Number(item.cantidad || 0)),
            formatMoney(item.precio_unitario),
            String(Number(item.descuento || 0)),
            formatMoney(item.subtotal),
          ])
        : [[
            TIPO_LABELS[documento.tipo_documento] || documento.tipo_documento,
            documento.folio || '-',
            contacto?.nombre || '-',
            ESTADO_LABELS[documento.estado] || documento.estado,
            formatDateChile(documento.fecha_emision),
            '-',
            '0',
            '0',
            '0',
            '0',
          ]]

    const totalRows = [
      ['', '', '', '', '', 'Subtotal neto', '', '', '', formatMoney(documento.subtotal_neto)],
      ['', '', '', '', '', 'Impuestos', '', '', '', formatMoney(documento.impuestos)],
      ['', '', '', '', '', 'Total', '', '', '', formatMoney(documento.total)],
    ]

    await downloadSimpleTablePdf({
      title: `Detalle documento ${documento.folio || documento.id}`,
      fileName: `documento_compra_${documento.folio || documento.id}_${getTodaySuffix()}.pdf`,
      headers: ['Tipo', 'Folio', 'Proveedor', 'Estado', 'Fecha emision', 'Producto', 'Cantidad', 'Precio unit.', 'Desc. %', 'Subtotal'],
      rows: [...itemRows, ...totalRows],
    })
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando documento...</p>
  }

  if (status === 'failed' || !documento) {
    return <p className="text-sm text-destructive">No se pudo cargar el documento.</p>
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Documento {documento.folio || '#'}</h2>
          <p className="text-sm text-muted-foreground">
            {TIPO_LABELS[documento.tipo_documento] || documento.tipo_documento} | {ESTADO_LABELS[documento.estado] || documento.estado}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:items-center sm:justify-end sm:gap-2">
          <ExportMenuButton
            variant="outline"
            size="md"
            fullWidth
            className="sm:w-auto"
            onExportExcel={handleExportExcel}
            onExportPdf={handleExportPdf}
          />
          <Link
            to={`/compras/documentos/${documento.id}/editar`}
            className={cn(buttonVariants({ variant: 'outline', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Editar
          </Link>
          <Link
            to="/compras/documentos"
            className={cn(buttonVariants({ variant: 'default', size: 'md', fullWidth: true }), 'sm:w-auto')}
          >
            Volver
          </Link>
        </div>
      </div>

      <div className="grid gap-4 rounded-md border border-border bg-card p-4 md:grid-cols-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">Proveedor</p>
          <p className="mt-1 text-sm">{contacto?.nombre || '-'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Fecha emision</p>
          <p className="mt-1 text-sm">{formatDateChile(documento.fecha_emision)}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-muted-foreground">Fecha recepcion</p>
          <p className="mt-1 text-sm">{formatDateChile(documento.fecha_recepcion)}</p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Producto</th>
              <th className="px-3 py-2 text-right font-medium">Cantidad</th>
              <th className="px-3 py-2 text-right font-medium">Precio unit.</th>
              <th className="px-3 py-2 text-right font-medium">Desc. %</th>
              <th className="px-3 py-2 text-right font-medium">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td className="px-3 py-3 text-muted-foreground" colSpan={5}>
                  Sin items asociados.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="px-3 py-2">{productoById.get(String(item.producto))?.nombre || item.descripcion || '-'}</td>
                  <td className="px-3 py-2 text-right">{Number(item.cantidad || 0).toLocaleString('es-CL')}</td>
                  <td className="px-3 py-2 text-right">{formatMoney(item.precio_unitario)}</td>
                  <td className="px-3 py-2 text-right">{Number(item.descuento || 0).toLocaleString('es-CL')}</td>
                  <td className="px-3 py-2 text-right">{formatMoney(item.subtotal)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex justify-end">
        <div className="w-full max-w-xs space-y-1 rounded-md border border-border bg-card p-4 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Subtotal neto</span>
            <span>{formatMoney(documento.subtotal_neto)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Impuestos</span>
            <span>{formatMoney(documento.impuestos)}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-1 font-semibold">
            <span>Total</span>
            <span>{formatMoney(documento.total)}</span>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ComprasDocumentosDetailPage
