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

function InventarioAjustesMasivosDetailPage() {
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
        const data = await inventarioApi.getOne(inventarioApi.endpoints.ajustesMasivos, id)
        setDocumento(data)
        setStatus('succeeded')
      } catch (error) {
        setStatus('failed')
        toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el ajuste masivo.' }))
      }
    }
    void loadData()
  }, [id])

  const exportRows = (documento?.items || []).map((item) => ({
    producto: item.producto_nombre || '-',
    bodega: item.bodega_nombre || '-',
    stock_actual: formatNumber(item.stock_actual),
    stock_objetivo: formatNumber(item.stock_objetivo),
    diferencia: formatNumber(item.diferencia),
    movimiento: item.movimiento || '-',
  }))

  const handleExportExcel = async () => {
    if (!documento) return
    await downloadExcelFile({
      sheetName: 'AjusteMasivo',
      fileName: `ajuste_masivo_${documento.numero || documento.id}_${getChileDateSuffix()}.xlsx`,
      columns: [
        { header: 'Producto', key: 'producto', width: 30 },
        { header: 'Bodega', key: 'bodega', width: 24 },
        { header: 'Stock actual', key: 'stock_actual', width: 16 },
        { header: 'Stock objetivo', key: 'stock_objetivo', width: 16 },
        { header: 'Diferencia', key: 'diferencia', width: 16 },
        { header: 'Movimiento', key: 'movimiento', width: 18 },
      ],
      rows: exportRows,
    })
  }

  const handleExportPdf = async () => {
    if (!documento) return
    await downloadSimpleTablePdf({
      title: `Ajuste masivo ${documento.numero || documento.id}`,
      fileName: `ajuste_masivo_${documento.numero || documento.id}_${getChileDateSuffix()}.pdf`,
      headers: ['Producto', 'Bodega', 'Stock actual', 'Stock objetivo', 'Diferencia'],
      rows: exportRows.map((row) => [row.producto, row.bodega, row.stock_actual, row.stock_objetivo, row.diferencia]),
    })
  }

  const handleDuplicate = async () => {
    setDuplicating(true)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.ajustesMasivos, id, 'duplicar')
      toast.success(`Borrador ${data.numero} generado correctamente.`)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo duplicar el ajuste masivo.' }))
    } finally {
      setDuplicating(false)
    }
  }

  const handleConfirm = async () => {
    setConfirming(true)
    try {
      const data = await inventarioApi.executeDetailAction(inventarioApi.endpoints.ajustesMasivos, id, 'confirmar')
      setDocumento(data)
      toast.success(`Ajuste masivo ${data.numero} confirmado correctamente.`)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo confirmar el ajuste masivo.' }))
    } finally {
      setConfirming(false)
    }
  }

  if (status === 'loading') {
    return <p className="text-sm text-muted-foreground">Cargando ajuste masivo...</p>
  }

  if (status === 'failed' || !documento) {
    return <p className="text-sm text-destructive">No se pudo cargar el ajuste masivo.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Detalle ajuste masivo</h2>
          <p className="text-sm text-muted-foreground">
            {documento.numero} | {documento.confirmado_en ? `confirmado ${formatDateTimeChile(documento.confirmado_en)}` : 'borrador pendiente de confirmacion'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {documento.estado === 'BORRADOR' && canEditInventario ? (
            <>
              <Button type="button" variant="outline" onClick={() => navigate(`/inventario/ajustes-masivos?draft=${documento.id}`)}>
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
          <Link to="/inventario/ajustes-masivos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>Volver</Link>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Estado</p>
          <p className="mt-1 text-lg font-semibold">{documento.estado}</p>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Motivo</p>
          <p className="mt-1 text-lg font-semibold">{documento.motivo}</p>
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
              <th className="px-3 py-2 text-left font-medium">Bodega</th>
              <th className="px-3 py-2 text-left font-medium">Stock actual</th>
              <th className="px-3 py-2 text-left font-medium">Stock objetivo</th>
              <th className="px-3 py-2 text-left font-medium">Diferencia</th>
            </tr>
          </thead>
          <tbody>
            {exportRows.map((row, index) => (
              <tr key={`${row.movimiento}-${index}`} className="border-t border-border">
                <td className="px-3 py-2">{row.producto}</td>
                <td className="px-3 py-2">{row.bodega}</td>
                <td className="px-3 py-2">{row.stock_actual}</td>
                <td className="px-3 py-2">{row.stock_objetivo}</td>
                <td className="px-3 py-2">{row.diferencia}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export default InventarioAjustesMasivosDetailPage
