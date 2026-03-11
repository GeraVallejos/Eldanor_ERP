import { useMemo, useState } from 'react'

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

export function useTableSorting(rows, { accessors = {}, initialKey = null, initialDirection = 'asc' } = {}) {
  const [sort, setSort] = useState({ key: initialKey, direction: initialDirection })

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

  const toggleSort = (key) => {
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
    sort,
    toggleSort,
    getSortIndicator,
  }
}
