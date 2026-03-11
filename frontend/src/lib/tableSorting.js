import { useEffect, useMemo, useState } from 'react'

function normalizeSortValue(value) {
  if (value === null || value === undefined) {
    return ''
  }

  if (typeof value === 'number') {
    return value
  }

  const asNumber = Number(value)
  if (!Number.isNaN(asNumber) && String(value).trim() !== '') {
    return asNumber
  }

  return String(value).toLowerCase()
}

function compareValues(left, right) {
  const a = normalizeSortValue(left)
  const b = normalizeSortValue(right)

  if (typeof a === 'number' && typeof b === 'number') {
    return a - b
  }

  return String(a).localeCompare(String(b), 'es', { sensitivity: 'base', numeric: true })
}

export function useTableSorting(rows, { accessors = {}, initialKey = null, initialDirection = 'asc', pageSize = 20 } = {}) {
  const [sort, setSort] = useState({ key: initialKey, direction: initialDirection })
  const [currentPage, setCurrentPage] = useState(1)

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setCurrentPage(1)
    }, 0)

    return () => clearTimeout(timeoutId)
  }, [rows])

  const sortedRows = useMemo(() => {
    if (!sort.key) {
      return rows
    }

    const getter = accessors[sort.key] || ((row) => row?.[sort.key])
    const sorted = [...rows].sort((left, right) => {
      const result = compareValues(getter(left), getter(right))
      return sort.direction === 'asc' ? result : -result
    })

    return sorted
  }, [rows, sort, accessors])

  const totalRows = sortedRows.length
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize))
  const clampedPage = Math.min(currentPage, totalPages)

  const paginatedRows = useMemo(() => {
    const start = (clampedPage - 1) * pageSize
    return sortedRows.slice(start, start + pageSize)
  }, [sortedRows, clampedPage, pageSize])

  const toggleSort = (key) => {
    setCurrentPage(1)
    setSort((prev) => {
      if (prev.key !== key) {
        return { key, direction: 'asc' }
      }

      return { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
    })
  }

  const getSortIndicator = (key) => {
    if (sort.key !== key) {
      return '↕'
    }

    return sort.direction === 'asc' ? '↑' : '↓'
  }

  return {
    sortedRows,
    paginatedRows,
    sort,
    toggleSort,
    getSortIndicator,
    currentPage: clampedPage,
    totalPages,
    totalRows,
    pageSize,
    nextPage: () => setCurrentPage((p) => Math.min(p + 1, totalPages)),
    prevPage: () => setCurrentPage((p) => Math.max(p - 1, 1)),
  }
}
