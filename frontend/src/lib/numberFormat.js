export function formatSmartNumber(value, options = {}) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }

  const { maximumFractionDigits = 2, locale = 'es-CL' } = options

  return num.toLocaleString(locale, {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  })
}

export function formatCurrencyCLP(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '$ 0'
  }

  return `$ ${num.toLocaleString('es-CL', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`
}

export function toIntegerString(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0'
  }
  return String(Math.round(num))
}

export function toQuantityString(value) {
  const normalized = String(value ?? '').replace(',', '.').trim()
  if (!normalized) {
    return '0'
  }

  const num = Number(normalized)
  if (!Number.isFinite(num) || num < 0) {
    return '0'
  }

  return String(num)
}

const DEFAULT_NUMERIC_NORMALIZERS = {
  cantidad: toQuantityString,
  precio_unitario: toIntegerString,
  precio_referencia: toIntegerString,
  precio_costo: toIntegerString,
  tasa: toQuantityString,
  tasa_referencia: toQuantityString,
  subtotal: toIntegerString,
  total: toIntegerString,
  descuento: toIntegerString,
  decimales: toIntegerString,
}

export function normalizeNumericInputByField(field, value, normalizers = DEFAULT_NUMERIC_NORMALIZERS) {
  const normalize = normalizers?.[field]
  if (typeof normalize !== 'function') {
    return value
  }
  return normalize(value)
}

export function normalizeObjectNumericFields(data, normalizers = DEFAULT_NUMERIC_NORMALIZERS) {
  const source = data || {}
  const next = { ...source }

  Object.entries(normalizers).forEach(([field, normalize]) => {
    if (Object.prototype.hasOwnProperty.call(source, field) && typeof normalize === 'function') {
      next[field] = normalize(source[field])
    }
  })

  return next
}
