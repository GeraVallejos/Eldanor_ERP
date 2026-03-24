import Button from '@/components/ui/Button'

function ActiveSearchFilter({
  query,
  activeLabel = '',
  filteredCount,
  totalCount,
  noun = 'registros',
  onClear,
  className = '',
}) {
  const normalizedQuery = String(query || '').trim()
  const normalizedLabel = String(activeLabel || '').trim()
  const displayLabel = normalizedLabel || (normalizedQuery ? `"${normalizedQuery}"` : '')

  if (!displayLabel) {
    return null
  }

  return (
    <div className={`flex flex-col gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-950 sm:flex-row sm:items-center sm:justify-between ${className}`}>
      <p>
        Mostrando {filteredCount} de {totalCount} {noun} para {displayLabel}.
      </p>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="border-sky-300 text-sky-950 hover:bg-sky-100"
        onClick={onClear}
      >
        Limpiar filtro
      </Button>
    </div>
  )
}

export default ActiveSearchFilter
