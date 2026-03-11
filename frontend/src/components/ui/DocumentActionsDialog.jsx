import Button from '@/components/ui/Button'

/**
 * Componente reutilizable para acciones de documentos/órdenes
 * Soporta: corregir (con motivo), duplicar, anular, eliminar
 *
 * Props:
 * - actionType: 'corregir' | 'duplicar' | 'anular' | 'eliminar'
 * - open: boolean
 * - loading: boolean
 * - onConfirm: () => void
 * - onCancel: () => void
 * - value: string (solo para 'corregir')
 * - onChange: (value) => void (solo para 'corregir')
 * - item: { numero?, folio? } para mostrar en el dialog
 */
function DocumentActionsDialog({
  actionType = 'corregir',
  open = false,
  loading = false,
  onConfirm = () => {},
  onCancel = () => {},
  value = '',
  onChange = () => {},
  item = null,
}) {
  if (!open) return null

  const titles = {
    corregir: 'Corregir documento',
    duplicar: 'Duplicar documento',
    anular: 'Anular documento',
    eliminar: 'Eliminar documento',
  }

  const descriptions = {
    corregir: item?.folio
      ? `Se anulará el documento ${item.folio} y se creará un nuevo borrador.`
      : 'Se anulará el documento y se creará un nuevo borrador.',
    duplicar: item?.numero || item?.folio
      ? `Se creará una copia del documento ${item.numero || item.folio} en estado borrador que podrá revisar y confirmar.`
      : 'Se creará una copia del documento en estado borrador que podrá revisar y confirmar.',
    anular: item?.numero || item?.folio
      ? `Se anulará el documento ${item.numero || item.folio}. Esta acción no se puede deshacer.`
      : 'Se anulará el documento. Esta acción no se puede deshacer.',
    eliminar: item?.numero || item?.folio
      ? `Se eliminará el documento ${item.numero || item.folio}. Esta acción no se puede deshacer.`
      : 'Se eliminará el documento. Esta acción no se puede deshacer.',
  }

  const confirmLabels = {
    corregir: 'Corregir',
    duplicar: 'Duplicar',
    anular: 'Anular',
    eliminar: 'Eliminar',
  }

  const showReasonInput = actionType === 'corregir'
  const isDestructive = actionType === 'anular' || actionType === 'eliminar'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-md border border-border bg-card shadow-lg">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-lg font-semibold">{titles[actionType]}</h3>
        </div>

        <div className="px-4 py-4">
          <p className="text-sm text-muted-foreground mb-4">{descriptions[actionType]}</p>

          {showReasonInput && (
            <div className="mb-4">
              <label className="text-sm font-medium">Motivo de la corrección</label>
              <textarea
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder="Indique el motivo por el cual se está corrigiendo este documento..."
                className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                rows={4}
              />
            </div>
          )}
        </div>

        <div className="flex gap-2 border-t border-border px-4 py-3">
          <Button
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={loading}
            className="flex-1"
          >
            Cancelar
          </Button>
          <Button
            variant={isDestructive ? 'outline' : 'default'}
            size="sm"
            onClick={onConfirm}
            disabled={loading || (showReasonInput && !value.trim())}
            className={
              isDestructive
                ? 'flex-1 border-destructive/40 text-destructive hover:bg-destructive/10'
                : 'flex-1'
            }
          >
            {loading ? 'Procesando...' : confirmLabels[actionType]}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default DocumentActionsDialog
