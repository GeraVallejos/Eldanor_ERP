import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '@/api/client'
import { normalizeApiError } from '@/api/errors'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'
import { formatMoney } from '@/modules/ventas/utils'

function VentasResumenPage() {
  const [resumen, setResumen] = useState(null)

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void api
        .get('/facturas-venta/resumen_operativo/', { suppressGlobalErrorToast: true })
        .then((response) => setResumen(response.data))
        .catch((error) => {
          toast.error(normalizeApiError(error, { fallback: 'No se pudo cargar el resumen de ventas.' }))
        })
    }, 0)
    return () => clearTimeout(timeoutId)
  }, [])

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Resumen de ventas</h2>
        <p className="text-sm text-muted-foreground">
          Vista ejecutiva de facturacion, cartera y accesos rapidos a los flujos comerciales.
        </p>
      </div>

      {resumen ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Facturas</p>
            <p className="mt-2 text-2xl font-semibold">{resumen.total_documentos || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">Emitidas: {resumen.emitidas || 0}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Facturacion total</p>
            <p className="mt-2 text-2xl font-semibold">{formatMoney(resumen.monto_total || 0)}</p>
            <p className="mt-1 text-sm text-muted-foreground">Emitido: {formatMoney(resumen.monto_emitido || 0)}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Cartera a vigilar</p>
            <p className="mt-2 text-2xl font-semibold">{resumen.vencidas || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">Vencido: {formatMoney(resumen.monto_vencido || 0)}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Proximas a vencer</p>
            <p className="mt-2 text-2xl font-semibold">{resumen.por_vencer_7_dias || 0}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Monto: {formatMoney(resumen.monto_por_vencer_7_dias || 0)} / Borradores: {resumen.borradores || 0}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Operacion comercial</p>
          <h3 className="mt-1 text-lg font-semibold">Pedidos</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Gestiona oportunidades convertidas en pedidos y seguimiento comercial.
          </p>
          <Link to="/ventas/pedidos" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a pedidos
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Despacho</p>
          <h3 className="mt-1 text-lg font-semibold">Guias</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Controla documentos de salida fisica y su trazabilidad operativa.
          </p>
          <Link to="/ventas/guias" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a guias
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Facturacion</p>
          <h3 className="mt-1 text-lg font-semibold">Facturas</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Opera emision y anulacion sobre el listado de facturas de venta.
          </p>
          <Link to="/ventas/facturas" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a facturas
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Ajustes comerciales</p>
          <h3 className="mt-1 text-lg font-semibold">Notas de credito</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Gestiona devoluciones, ajustes y anulaciones asociadas a ventas.
          </p>
          <Link to="/ventas/notas" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a notas
          </Link>
        </div>
        <div className="rounded-md border border-border bg-card p-4">
          <p className="text-sm text-muted-foreground">Consulta y exportacion</p>
          <h3 className="mt-1 text-lg font-semibold">Reportes</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Descarga reportes ejecutivos de facturacion y cartera comercial.
          </p>
          <Link to="/ventas/reportes" className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'mt-4')}>
            Ir a reportes
          </Link>
        </div>
      </div>
    </section>
  )
}

export default VentasResumenPage
