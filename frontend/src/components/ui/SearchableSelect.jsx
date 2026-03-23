import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

function normalizeText(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

function isOptionMatch(option, query) {
  const target = `${option.label || ''} ${option.keywords || ''}`
  return normalizeText(target).includes(query)
}

function SearchableSelect({
  options,
  value,
  onChange,
  onSearchChange,
  placeholder = 'Buscar...',
  emptyText = 'Sin resultados',
  disabled = false,
  ariaLabel,
  className = '',
  inputClassName = '',
  maxVisibleOptions = 30,
  loading = false,
}) {
  const containerRef = useRef(null)
  const inputRef = useRef(null)
  const dropdownRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [cursor, setCursor] = useState(-1)
  const [dropdownStyle, setDropdownStyle] = useState(null)

  const selectedOption = useMemo(
    () => options.find((option) => String(option.value) === String(value)) || null,
    [options, value],
  )


  useEffect(() => {
    const onPointerDown = (event) => {
      const isInsideInput = containerRef.current?.contains(event.target)
      const isInsideDropdown = dropdownRef.current?.contains(event.target)

      if (!isInsideInput && !isInsideDropdown) {
        setOpen(false)
        setCursor(-1)
      }
    }

    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [])

  useEffect(() => {
    if (!open || !inputRef.current) {
      return
    }

    const updatePosition = () => {
      if (!inputRef.current) {
        return
      }

      const rect = inputRef.current.getBoundingClientRect()
      const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 800
      const spaceBelow = viewportHeight - rect.bottom - 8
      const maxHeight = Math.max(160, Math.min(320, spaceBelow))

      setDropdownStyle({
        position: 'fixed',
        top: `${rect.bottom + 4}px`,
        left: `${rect.left}px`,
        width: `${rect.width}px`,
        maxHeight: `${maxHeight}px`,
        zIndex: 1200,
      })
    }

    updatePosition()

    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [open])

  const normalizedQuery = normalizeText(query)
  const displayValue = open ? query : selectedOption?.label || ''

  const filteredOptions = useMemo(() => {
    if (!normalizedQuery) {
      return options.slice(0, maxVisibleOptions)
    }

    return options.filter((option) => isOptionMatch(option, normalizedQuery)).slice(0, maxVisibleOptions)
  }, [options, normalizedQuery, maxVisibleOptions])

  const commitOption = (option) => {
    onChange(String(option.value))
    setQuery(option.label)
    setOpen(false)
    setCursor(-1)
  }

  const handleClear = () => {
    setQuery('')
    onChange('')
    inputRef.current?.focus()
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          value={displayValue}
          aria-label={ariaLabel}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full rounded-md border border-input bg-background px-3 py-2 pr-8 text-sm ${inputClassName}`}
          onFocus={() => {
            // Si no hay opcion seleccionada, limpia la query residual para que el campo abra limpio
            if (!selectedOption) {
              setQuery('')
            }
            setOpen(true)
            setCursor(-1)
          }}
          onChange={(event) => {
            const nextQuery = event.target.value
            setQuery(nextQuery)
            setOpen(true)
            setCursor(-1)
            if (typeof onSearchChange === 'function') {
              onSearchChange(nextQuery)
            }
            if (!nextQuery.trim()) {
              onChange('')
            }
          }}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') {
            event.preventDefault()
            if (!open) {
              setOpen(true)
              return
            }
            if (filteredOptions.length > 0) {
              setCursor((prev) => Math.min(prev + 1, filteredOptions.length - 1))
            }
            return
          }

          if (event.key === 'ArrowUp') {
            event.preventDefault()
            if (filteredOptions.length > 0) {
              setCursor((prev) => Math.max(prev - 1, 0))
            }
            return
          }

          if (event.key === 'Enter') {
            if (open && filteredOptions.length > 0) {
              event.preventDefault()
              const option = cursor >= 0 ? filteredOptions[cursor] : filteredOptions[0]
              if (option) {
                commitOption(option)
              }
            }
            return
          }

          if (event.key === 'Escape') {
            setOpen(false)
            setCursor(-1)
          }
        }}
        onBlur={() => {
          setOpen(false)
          setCursor(-1)
        }}
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Limpiar búsqueda"
          >
            x
          </button>
        )}
      </div>

      {open && dropdownStyle
        ? createPortal(
            <div
              ref={dropdownRef}
              style={dropdownStyle}
              className="overflow-auto rounded-md border border-border bg-card shadow-lg"
            >
              {filteredOptions.length === 0 ? (
                <div className="px-3 py-2 text-xs text-muted-foreground">{loading ? 'Buscando...' : emptyText}</div>
              ) : (
                filteredOptions.map((option, index) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`block w-full px-3 py-2 text-left text-sm hover:bg-muted ${
                      index === cursor ? 'bg-muted' : ''
                    }`}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => commitOption(option)}
                  >
                    {option.label}
                  </button>
                ))
              )}
            </div>,
            document.body,
          )
        : null}
    </div>
  )
}

export default SearchableSelect
