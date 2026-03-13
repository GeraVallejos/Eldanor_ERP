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

  return `$ ${Math.round(num).toLocaleString('es-CL')}`
}
