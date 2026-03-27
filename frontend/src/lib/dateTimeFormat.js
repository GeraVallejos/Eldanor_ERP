const CHILE_TIME_ZONE = 'America/Santiago'
const DATE_ONLY_REGEX = /^\d{4}-\d{2}-\d{2}$/

function toValidDate(value) {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }

  if (value === null || value === undefined || value === '') {
    return null
  }

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTimeChile(value) {
  const date = toValidDate(value)
  if (!date) {
    return '-'
  }

  return new Intl.DateTimeFormat('es-CL', {
    timeZone: CHILE_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

export function formatDateChile(value) {
  if (typeof value === 'string' && DATE_ONLY_REGEX.test(value)) {
    const [year, month, day] = value.split('-')
    return `${day}-${month}-${year}`
  }

  const date = toValidDate(value)
  if (!date) {
    return '-'
  }

  return new Intl.DateTimeFormat('es-CL', {
    timeZone: CHILE_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

export function getChileDateSuffix(value = new Date()) {
  const date = toValidDate(value)
  if (!date) {
    return 'fecha_invalida'
  }

  return new Intl.DateTimeFormat('sv-SE', {
    timeZone: CHILE_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}
