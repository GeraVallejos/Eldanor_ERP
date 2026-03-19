import { useEffect, useRef, useState } from 'react'
import Button from '@/components/ui/Button'
import { cn } from '@/lib/utils'

function MenuButton({
  onExportExcel,
  onExportPdf,
  items,
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
  const menuItems = items ?? [
    onExportExcel
      ? {
          key: 'excel',
          label: 'Exportar Excel',
          onClick: onExportExcel,
        }
      : null,
    onExportPdf
      ? {
          key: 'pdf',
          label: 'Exportar PDF',
          onClick: onExportPdf,
        }
      : null,
  ].filter(Boolean)

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
          {menuItems.map((item, index) => (
            <button
              key={item.key ?? item.label}
              type="button"
              className={cn(
                'block w-full rounded px-3 py-2 text-left hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60',
                index > 0 && 'mt-1'
              )}
              onClick={() => {
                setOpen(false)
                if (item.onClick) {
                  void item.onClick()
                }
              }}
              disabled={item.disabled}
            >
              <span className="block text-sm font-medium">{item.label}</span>
              {item.description ? (
                <span className="block text-xs text-muted-foreground">{item.description}</span>
              ) : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export default MenuButton