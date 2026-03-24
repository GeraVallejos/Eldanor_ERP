import { cn } from '@/lib/utils'

export function DetailRow({ label, value }) {
  return (
    <div className="rounded-lg border border-border bg-background/70 p-3">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  )
}

export function InfoCard({ title, description, children }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="text-lg font-semibold">{title}</h3>
      {description ? <p className="mt-1 text-sm text-muted-foreground">{description}</p> : null}
      <div className="mt-4">{children}</div>
    </div>
  )
}

export function SectionTabButton({ active, label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-full border px-4 py-2 text-sm font-medium transition-colors',
        active
          ? 'border-foreground bg-foreground text-background'
          : 'border-border bg-background text-foreground hover:bg-muted',
      )}
    >
      {label}
    </button>
  )
}

export function SeverityBadge({ severity }) {
  const normalizedSeverity = String(severity || 'INFO').toUpperCase()
  const toneClassName = {
    INFO: 'border-sky-200 bg-sky-50 text-sky-900',
    WARNING: 'border-amber-200 bg-amber-50 text-amber-900',
    ERROR: 'border-rose-200 bg-rose-50 text-rose-900',
    CRITICAL: 'border-red-200 bg-red-50 text-red-900',
  }[normalizedSeverity] || 'border-border bg-muted/40 text-foreground'

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium uppercase tracking-wide',
        toneClassName,
      )}
    >
      {normalizedSeverity}
    </span>
  )
}
