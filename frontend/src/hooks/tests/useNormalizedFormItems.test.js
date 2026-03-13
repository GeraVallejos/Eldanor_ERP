import { describe, expect, it } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useNormalizedFormItems } from '@/hooks/useNormalizedFormItems'

describe('useNormalizedFormItems', () => {
  it('normaliza campos numericos conocidos por default', () => {
    const { result } = renderHook(() => useNormalizedFormItems())

    expect(result.current.normalizeFieldValue('cantidad', '3,5')).toBe('3.5')
    expect(result.current.normalizeFieldValue('precio_unitario', '1290.4')).toBe('1290')
    expect(result.current.normalizeFieldValue('descripcion', 'Texto libre')).toBe('Texto libre')
  })

  it('normaliza coleccion de items con reglas custom', () => {
    const { result } = renderHook(() =>
      useNormalizedFormItems({
        normalizers: {
          qty: (value) => String(Math.max(0, Number(value) || 0)),
        },
      }),
    )

    const rows = result.current.normalizeItemsCollection([
      { qty: '-1', label: 'A' },
      { qty: '2.5', label: 'B' },
    ])

    expect(rows).toEqual([
      { qty: '0', label: 'A' },
      { qty: '2.5', label: 'B' },
    ])
  })
})
