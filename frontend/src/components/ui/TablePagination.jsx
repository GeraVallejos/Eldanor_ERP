import Button from './Button'

export default function TablePagination({ currentPage, totalPages, totalRows, pageSize, onPrev, onNext }) {
  if (totalRows === 0) return null

  const start = (currentPage - 1) * pageSize + 1
  const end = Math.min(currentPage * pageSize, totalRows)

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-3 py-2 text-sm text-muted-foreground">
      <span>
        {start}–{end} de {totalRows}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onPrev}
          disabled={currentPage <= 1}
          className="h-7 px-3 text-xs"
        >
          Anterior
        </Button>
        <span className="tabular-nums text-xs">
          {currentPage} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={onNext}
          disabled={currentPage >= totalPages}
          className="h-7 px-3 text-xs"
        >
          Siguiente
        </Button>
      </div>
    </div>
  )
}
