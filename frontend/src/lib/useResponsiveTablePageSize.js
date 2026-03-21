import { useEffect, useState } from 'react'

function resolvePageSize({
  mobileRows,
  desktopMinRows,
  desktopMaxRows,
  reservedHeight,
  rowHeight,
  breakpoint,
}) {
  if (typeof window === 'undefined' || window.innerWidth < breakpoint) {
    return mobileRows
  }

  const availableHeight = Math.max(0, window.innerHeight - reservedHeight)
  const computedRows = Math.floor(availableHeight / rowHeight)

  return Math.max(desktopMinRows, Math.min(desktopMaxRows, computedRows || desktopMinRows))
}

export function useResponsiveTablePageSize({
  mobileRows = 10,
  desktopMinRows = 8,
  desktopMaxRows = 12,
  reservedHeight = 430,
  rowHeight = 44,
  breakpoint = 1024,
} = {}) {
  const [pageSize, setPageSize] = useState(() =>
    resolvePageSize({
      mobileRows,
      desktopMinRows,
      desktopMaxRows,
      reservedHeight,
      rowHeight,
      breakpoint,
    }),
  )

  useEffect(() => {
    const handleResize = () => {
      setPageSize(
        resolvePageSize({
          mobileRows,
          desktopMinRows,
          desktopMaxRows,
          reservedHeight,
          rowHeight,
          breakpoint,
        }),
      )
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [mobileRows, desktopMinRows, desktopMaxRows, reservedHeight, rowHeight, breakpoint])

  return pageSize
}
