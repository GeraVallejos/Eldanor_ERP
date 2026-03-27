import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import MenuButton from '@/components/ui/MenuButton'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateTimeChile, getChileDateSuffix } from '@/lib/dateTimeFormat'
import { formatSmartNumber } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { inventarioApi } from '@/modules/inventario/store'
import { downloadExcelFile } from '@/modules/shared/exports/downloadExcelFile'
import { downloadSimpleTablePdf } from '@/modules/shared/exports/downloadSimpleTablePdf'
import { usePermissions } from '@/modules/shared/auth/usePermission'

function formatNumber(value) {
  return formatSmartNumber(value, { maximumFractionDigits: 2 })
}

function InventarioTrasladosMasivosDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const permissions = usePermissions(['INVENTARIO.VER', 'INVENTARIO.EDITAR'])
  const canEditInventario = permissions['INVENTARIO.EDITAR']
  const [status, setStatus] = useState('idle')
  const [duplicating, setDuplicating] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [documento, setDocumento] = useState(null)

  useEffect(() => {
    const loadData = async () => {
      setStatus('loading')
      try {
        const data = await inventarioApi.getOne(inventarioApi.endpoints.trasladosMasivos, id)
        setDocumento(data)
        setStatus('succeeded')
      } catch (error) {
        setStatus('failed')
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el traslado masivo.' }))
      }
    }
    void loadData()
  }, [id])

  const exportRows = (documento?.items || []).map((item) => ({
    producto: item.producto_nombre || '-',
    cantidad: formatNumber(item.cantidad),
    salida: item.movimiento_salida || '-',
    entrada: item.movimiento_entrada || '-',
  }))

  const handleExportExcel = async () => {
    if (!documento) return
    await downloadExcelFile({
      sheetName: 'TrasladoMasivo',
      fileName: `traslado_masivo_${documento.numero || documento.id}_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Producto', key: 'producto', width: 30 },
        { header: 'Cantidad', key: 'cantidad', width: 14 },
        { header: 'Movimiento salida', key: 'salida', width: 18 },
        { header: 'Movimiento entrada', key: 'entrada', width: 18 },
      ],
      rows: exportRows,
    })
  }

  const handleExportPdf = async () => {
    if (!documento) return
    await downloadSimpleTablePdf({
      title: `Traslado masivo ${documento.numero || documento.id}`,
      fileName: `traslado_masivo_${documento.numero || documento.id}_${getChileDateSuffix()}.pdf`,
      headers: ['Producto', 'Cantidad', 'Movimiento salida', 'Movimiento entrada'],
      rows: exportRows.map((row) => [row.producto, row.cantidad, row.salida, row.entrada]),
    })
  }

  const handleDuplicate = async () => {
    setDuplicating(true)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.trasladosMasivos, id, 'duplicar')
      toast.success(`Borrador ${data.numero} generado correctamente.`)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo duplicar el traslado masivo.' }))
    } finally {
      setDuplicating(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.trasladosMasivos, id, 'confirmar')
      setDocumento(data)
      toast.success(`Traslado masivo ${data.numero} confirmado correctamente.`)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo confirmar el traslado masivo.' }))
    } finally {
      setConfirming(false)
    }
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando traslado masivo...</p>
  }

  if (status === 'failed' || !documento) {
    return <p className="text-sm text-destructive">No se pudo cargar el traslado masivo.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Detalle traslado masivo</h2>
          <p className="text-sm text-muted-foreground">
            {documento.numero} | {documento.confirmado_en ? `confirmado ${formatDateTimeChile(documento.confirmado_en)}` : 'borrador pendiente de confirmacion'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {documento.estado === 'BORRADOR' && canEditInventario ? (
            <>
              <Button type="button" variant="outline" onClick={() => navigate(`/inventario/traslados-masivos?draft=${documento.id}`)}>
                Editar borrador
              </Button>
              <Button type="button" onClick={handleConfirm} disabled={confirming}>
                {confirming ? 'Confirmando...' : 'Confirmar borrador'}
              </Button>
            </>
          ) : null}
          {canEditInventario ? (
            <Button type="button" variant="outline" onClick={handleDuplicate} disabled={duplicating}>
              {duplicating ? 'Duplicando...' : 'Duplicar documento'}
            </Button>
          ) : null}
          <MenuButton variant="outline" onExportExcel={handleExportExcel} onExportPdf={handleExportPdf} disabled={exportRows.length === 0} />
          <Link to="/inventario/traslados-masivos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-5">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Estado</p>
          <p className="mt-1 text-lg font-semibold">{documento.estado}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Origen</p>
          <p className="mt-1 text-lg font-semibold">{documento.bodega_origen_nombre}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Destino</p>
          <p className="mt-1 text-lg font-semibold">{documento.bodega_destino_nombre}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Lineas</p>
          <p className="mt-1 text-lg font-semibold">{documento.items?.length || 0}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Referencia</p>
          <p className="mt-1 text-sm font-medium">{documento.referencia || '-'}</p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40">
            <tr>
              <th className="px-3 py-2 text-left font-medium">Producto</th>
              <th className="px-3 py-2 text-left font-medium">Cantidad</th>
              <th className="px-3 py-2 text-left font-medium">Movimiento salida</th>
              <th className="px-3 py-2 text-left font-medium">Movimiento entrada</th>
            </tr>
          </thead>
          <tbody>
            {exportRows.map((row, index) => (
              <tr key={`${row.salida}-${index}`} className="border-t border-border">
                <td className="px-3 py-2">{row.producto}</td>
                <td className="px-3 py-2">{row.cantidad}</td>
                <td className="px-3 py-2">{row.salida}</td>
                <td className="px-3 py-2">{row.entrada}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default InventarioTrasladosMasivosDetailPage
