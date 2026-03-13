import { useEffect, useRef, useState } from 'react'
import Button from '@/components/ui/Button'
import { cn } from '@/lib/utils'

function ExportMenuButton({
  onExportExcel,
  onExportPdf,
  disabled = false,
  variant = 'outline',
  size = 'md',
  fullWidth = false,
  className,
  menuClassName,
  label = 'Exportar',
}) {
  const containerRef = useRef(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) {
      return undefined
    }

    const handlePointerDown = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [open])

  return (
    <div className={cn('relative', className)} ref={containerRef}>
      <Button
        type="button"
        variant={variant}
        size={size}
        fullWidth={fullWidth}
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled}
      >
        {label}
      </Button>

      {open ? (
        <div className={cn('absolute right-0 z-20 mt-2 w-40 rounded-md border border-border bg-popover p-1 shadow-md', menuClassName)}>
          <button
            type="button"
            className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-muted"
            onClick={() => {
              setOpen(false)
              if (onExportExcel) {
                void onExportExcel()
              }
            }}
          >
            Exportar Excel
          </button>
          <button
            type="button"
            className="mt-1 block w-full rounded px-3 py-2 text-left text-sm hover:bg-muted"
            onClick={() => {
              setOpen(false)
              if (onExportPdf) {
                void onExportPdf()
              }
            }}
          >
            Exportar PDF
          </button>
        </div>
      ) : null}
    </div>
  )
}

export default ExportMenuButton
