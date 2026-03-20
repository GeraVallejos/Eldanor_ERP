import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import Button from '@/components/ui/Button'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatDateChile } from '@/lib/dateTimeFormat'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'
import { usePermission } from '@/modules/shared/auth/usePermission'

function buildReferenceLink(asiento) {
  const referenceId = asiento?.referencia_id
  if (!referenceId) {
    return null
  }

  switch (asiento.referencia_tipo) {
    case 'FACTURA_VENTA':
      return { label: 'Abrir factura de venta', to: `/ventas/facturas/${referenceId}/editar` }
    case 'NOTA_CREDITO_VENTA':
    case 'NOTA_CREDITO_VENTA_REVERSA':
      return { label: 'Abrir nota de credito', to: `/ventas/notas/${referenceId}/editar` }
    case 'DOCUMENTO_COMPRA':
    case 'DOCUMENTO_COMPRA_REVERSA':
      return { label: 'Abrir documento de compra', to: `/compras/documentos/${referenceId}` }
    case 'MOVIMIENTO_BANCARIO':
      return { label: 'Ir a tesoreria bancaria', to: '/tesoreria/bancos' }
    case 'REVERSA_ASIENTO':
      return { label: 'Ir a asientos contables', to: '/contabilidad/asientos' }
    default:
      return null
  }
}

function ContabilidadAsientoDetailPage() {
  const { id } = useParams()
  const canView = usePermission('CONTABILIDAD.VER')
  const canManage = usePermission('CONTABILIDAD.CONTABILIZAR')
  const [loading, setLoading] = useState(true)
  const [contabilizando, setContabilizando] = useState(false)
  const [asiento, setAsiento] = useState(null)
  const [cuentas, setCuentas] = useState([])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [{ data: asientoData }, { data: cuentasData }] = await Promise.all([
        api.get(`/asientos-contables/${id}/`, { suppressGlobalErrorToast: true }),
        api.get('/plan-cuentas/', { suppressGlobalErrorToast: true }),
      ])
      setAsiento(asientoData)
      setCuentas(Array.isArray(cuentasData?.results) ? cuentasData.results : Array.isArray(cuentasData) ? cuentasData : [])
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el asiento contable.' }))
      setAsiento(null)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    if (!canView) {
      return
    }
    void loadData()
  }, [canView, loadData])

  const cuentasById = useMemo(() => {
    const map = new Map()
    cuentas.forEach((cuenta) => {
      map.set(String(cuenta.id), cuenta)
    })
    return map
  }, [cuentas])

  const referenceLink = useMemo(() => buildReferenceLink(asiento), [asiento])

  const handleContabilizar = async () => {
    if (!asiento) {
      return
    }
    setContabilizando(true)
    try {
      const { data } = await api.post(`/asientos-contables/${asiento.id}/contabilizar/`, {}, { suppressGlobalErrorToast: true })
      setAsiento(data)
      toast.success('Asiento contabilizado.')
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo contabilizar el asiento.' }))
    } finally {
      setContabilizando(false)
    }
  }

  if (!canView) {
    return <p className="text-sm text-destructive">No tiene permiso para revisar el detalle contable.</p>
  }

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando asiento contable...</p>
  }

  if (!asiento) {
    return <p className="text-sm text-destructive">No se pudo cargar el asiento contable.</p>
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Asiento {asiento.numero}</h2>
          <p className="text-sm text-muted-foreground">
            Glosa: <span className="font-medium text-foreground">{asiento.glosa}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {referenceLink ? (
            <Link to={referenceLink.to} className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
              {referenceLink.label}
            </Link>
          ) : null}
          {canManage && asiento.estado === 'BORRADOR' ? (
            <Button type="button" onClick={handleContabilizar} disabled={contabilizando}>
              {contabilizando ? 'Procesando...' : 'Contabilizar'}
            </Button>
          ) : null}
          <Link to="/contabilidad/asientos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }))}>
            Volver
          </Link>
        </div>
      </div>

      <div className="grid gap-3 rounded-xl border border-border bg-card p-4 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Fecha</p>
          <p className="mt-1 text-sm font-medium">{formatDateChile(asiento.fecha)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Estado</p>
          <p className="mt-1 text-sm font-medium">{asiento.estado}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Origen</p>
          <p className="mt-1 text-sm font-medium">{asiento.origen}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Cuadratura</p>
          <p className={`mt-1 text-sm font-medium ${asiento.cuadrado ? 'text-emerald-600' : 'text-amber-600'}`}>
            {asiento.cuadrado ? 'Cuadrado' : 'Revisar'}
          </p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Referencia tipo</p>
          <p className="mt-1 text-sm">{asiento.referencia_tipo || '-'}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Referencia id</p>
          <p className="mt-1 break-all text-sm">{asiento.referencia_id || '-'}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Total debe</p>
          <p className="mt-1 text-sm font-medium">{formatCurrencyCLP(asiento.total_debe)}</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Total haber</p>
          <p className="mt-1 text-sm font-medium">{formatCurrencyCLP(asiento.total_haber)}</p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card p-4">
        <div className="mb-3">
          <h3 className="text-lg font-semibold">Movimientos del asiento</h3>
          <p className="text-sm text-muted-foreground">Detalle de cuentas afectadas, glosa por linea y montos registrados.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Cuenta</th>
                <th className="px-3 py-2 text-left font-medium">Glosa</th>
                <th className="px-3 py-2 text-right font-medium">Debe</th>
                <th className="px-3 py-2 text-right font-medium">Haber</th>
              </tr>
            </thead>
            <tbody>
              {(asiento.movimientos || []).length === 0 ? (
                <tr>
                  <td className="px-3 py-3 text-muted-foreground" colSpan={4}>Este asiento no tiene movimientos visibles.</td>
                </tr>
              ) : (
                asiento.movimientos.map((movimiento) => {
                  const cuenta = cuentasById.get(String(movimiento.cuenta))
                  return (
                    <tr key={movimiento.id} className="border-t border-border">
                      <td className="px-3 py-2">
                        {cuenta ? `${cuenta.codigo} - ${cuenta.nombre}` : movimiento.cuenta}
                      </td>
                      <td className="px-3 py-2">{movimiento.glosa || asiento.glosa || '-'}</td>
                      <td className="px-3 py-2 text-right">{formatCurrencyCLP(movimiento.debe)}</td>
                      <td className="px-3 py-2 text-right">{formatCurrencyCLP(movimiento.haber)}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
            {(asiento.movimientos || []).length > 0 ? (
              <tfoot>
                <tr className="border-t border-border bg-muted/20 font-medium">
                  <td className="px-3 py-2" colSpan={2}>Totales</td>
                  <td className="px-3 py-2 text-right">{formatCurrencyCLP(asiento.total_debe)}</td>
                  <td className="px-3 py-2 text-right">{formatCurrencyCLP(asiento.total_haber)}</td>
                </tr>
              </tfoot>
            ) : null}
          </table>
        </div>
      </div>
    </section>
  )
}

export default ContabilidadAsientoDetailPage
