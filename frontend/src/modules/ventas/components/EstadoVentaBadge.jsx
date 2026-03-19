import { cn } from '@/lib/utils'
import { formatEstadoLabel } from '@/modules/ventas/utils'

const toneByEstado = {
  BORRADOR: 'bg-muted text-muted-foreground border-border',
  CONFIRMADO: 'bg-blue-100 text-blue-700 border-blue-200',
  EN_PROCESO: 'bg-amber-100 text-amber-700 border-amber-200',
  DESPACHADO: 'bg-sky-100 text-sky-700 border-sky-200',
  FACTURADO: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  EMITIDA: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  CONFIRMADA: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  ANULADO: 'bg-rose-100 text-rose-700 border-rose-200',
  ANULADA: 'bg-rose-100 text-rose-700 border-rose-200',
}

function EstadoVentaBadge({ estado }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium uppercase tracking-wide',
        toneByEstado[String(estado || '').toUpperCase()] || 'bg-muted text-muted-foreground border-border',
      )}
    >
      {formatEstadoLabel(estado)}
    </span>
  )
}

export default EstadoVentaBadge
