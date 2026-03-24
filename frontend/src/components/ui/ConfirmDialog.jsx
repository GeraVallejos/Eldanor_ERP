import Button from '@/components/ui/Button'

function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  loading = false,
  confirmDisabled = false,
  hideConfirm = false,
  onConfirm,
  onCancel,
}) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-90 flex items-center justify-center bg-foreground/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-4 shadow-xl">
        <h3 className="text-lg font-semibold">{title}</h3>
        {description ? (
          typeof description === 'string'
            ? <p className="mt-2 text-sm text-muted-foreground">{description}</p>
            : <div className="mt-2 text-sm text-muted-foreground">{description}</div>
        ) : null}

        <div className="mt-4 flex items-center justify-end gap-2">
          <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          {hideConfirm ? null : (
            <Button
              type="button"
              variant="outline"
              onClick={onConfirm}
              disabled={loading || confirmDisabled}
              className="border-destructive/40 text-destructive hover:bg-destructive/10"
            >
              {loading ? 'Procesando...' : confirmLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog
