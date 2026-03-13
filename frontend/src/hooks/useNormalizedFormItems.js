import { useCallback } from 'react'
import { normalizeNumericInputByField, normalizeObjectNumericFields } from '@/lib/numberFormat'

export function useNormalizedFormItems(options = {}) {
  const { normalizers } = options

  const normalizeFieldValue = useCallback(
    (field, value) => normalizeNumericInputByField(field, value, normalizers),
    [normalizers],
  )

  const normalizeItemFields = useCallback(
    (item) => normalizeObjectNumericFields(item, normalizers),
    [normalizers],
  )

  const normalizeItemsCollection = useCallback(
    (items) => (Array.isArray(items) ? items.map((item) => normalizeItemFields(item)) : []),
    [normalizeItemFields],
  )

  return {
    normalizeFieldValue,
    normalizeItemFields,
    normalizeItemsCollection,
  }
}

export default useNormalizedFormItems