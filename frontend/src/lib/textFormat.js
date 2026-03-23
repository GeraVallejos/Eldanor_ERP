export function normalizeUpperInput(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .trimStart()
    .toUpperCase()
}
