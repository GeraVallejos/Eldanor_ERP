import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { formatCurrencyCLP } from '@/lib/numberFormat'
import { cn } from '@/lib/utils'

function formatMoney(value) {
  return formatCurrencyCLP(value)
}

function ComprasResumenPage() {
  const [resumen, setResumen] = useState(null)
  const [resumenDocumentos, setResumenDocumentos] = useState(null)

  const loadData = useCallback(async () => {
    try {
      const [{ data: ordenesData }, { data: documentosData }] = await Promise.all([
        api.get('/ordenes-compra/resumen_operativo/', { suppressGlobalErrorToast: true }),
        api.get('/documentos-compra/resumen_operativo/', { suppressGlobalErrorToast: true }),
      ])
      setResumen(ordenesData)
      setResumenDocumentos(documentosData)
    } catch (error) {
      toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el resumen de compras.' }))
    }
  }, [])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadData()
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [loadData])

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Resumen de compras</h2>
        <p className="text-sm text-muted-foreground">
          Vista ejecutiva del abastecimiento, avance documental y accesos rapidos a la operacion.
        </p>
      </div>

      {resumen ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Ordenes</p>
            <p className="mt-2 text-2xl font-semibold">{resumen.total_ordenes || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Pendientes de recepcion: {resumen.pendientes_recepcion || 0}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto comprometido</p>
            <p className="mt-2 text-2xl font-semibold">{formatMoney(resumen.monto_total || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Pendiente: {formatMoney(resumen.monto_pendiente || 0)}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Enviadas</p>
            <p className="mt-2 text-2xl font-semibold">{resumen.enviadas || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">Parciales: {resumen.parciales || 0}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Cierre de ciclo</p>
            <p className="mt-2 text-2xl font-semibold">{resumen.recibidas || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">Canceladas: {resumen.canceladas || 0}</p>
          </div>
        </div>
      ) : null}

      {resumenDocumentos ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Documentos de compra</p>
            <p className="mt-2 text-2xl font-semibold">{resumenDocumentos.total_documentos || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">Confirmados: {resumenDocumentos.confirmados || 0}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Monto documental</p>
            <p className="mt-2 text-2xl font-semibold">{formatMoney(resumenDocumentos.monto_total || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Confirmado: {formatMoney(resumenDocumentos.monto_confirmado || 0)}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Tipos de documento</p>
            <p className="mt-2 text-2xl font-semibold">{resumenDocumentos.facturas || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Guias: {resumenDocumentos.guias || 0} / Boletas: {resumenDocumentos.boletas || 0}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Pendientes documentales</p>
            <p className="mt-2 text-2xl font-semibold">{resumenDocumentos.sin_recepcion || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Borradores: {resumenDocumentos.borradores || 0} / Anulados: {resumenDocumentos.anulados || 0}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Operacion</p>
          <h3 className="mt-1 text-lg font-semibold">Ordenes de compra</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Gestiona solicitudes, aprobaciones y el backlog operativo del abastecimiento.
          </p>
          <Link to="/compras/ordenes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a ordenes
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Flujo documental</p>
          <h3 className="mt-1 text-lg font-semibold">Documentos</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Controla facturas, guias y su relacion con recepciones y stock.
          </p>
          <Link to="/compras/documentos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a documentos
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Recepcion fisica</p>
          <h3 className="mt-1 text-lg font-semibold">Recepciones</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Registra ingresos fisicos y seguimiento del pendiente operativo.
          </p>
          <Link to="/compras/recepciones" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a recepciones
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Consulta y exportacion</p>
          <h3 className="mt-1 text-lg font-semibold">Reportes</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Descarga reportes operativos y documentales del abastecimiento.
          </p>
          <Link to="/compras/reportes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a reportes
          </Link>
        </div>
      </div>
    </section>
  )
}

export default ComprasResumenPage
