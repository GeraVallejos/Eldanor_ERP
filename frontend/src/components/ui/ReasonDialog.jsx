import Button from '@/components/ui/Button'

function ReasonDialog({
  open,
  title,
  description,
  value,
  onChange,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  loading = false,
  onConfirm,
  onCancel,
}) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-4 shadow-xl">
        <h3 className="text-lg font-semibold">{title}</h3>
        {description ? <p className="mt-2 text-sm text-muted-foreground">{description}</p> : null}

        <label className="mt-4 block text-sm">
          Motivo
          <textarea
            value={value}
            onChange={(event) => onChange(event.target.value)}
            rows={4}
            placeholder="Describe brevemente el motivo de la correccion..."
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            disabled={loading}
          />
        </label>

        <div className="mt-4 flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button type="button" onClick={onConfirm} disabled={loading || !String(value || '').trim()}>
            {loading ? 'Procesando...' : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ReasonDialog
