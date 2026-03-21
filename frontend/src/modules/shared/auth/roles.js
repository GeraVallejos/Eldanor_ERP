function normalizeRoleCode(value) {
  return String(value || '').trim().toUpperCase()
}

export function getUserRoles(user) {
  const explicitRoles = Array.isArray(user?.roles) ? user.roles : []
  const fallbackRole = user?.rol ? [user.rol] : []
  const mergedRoles = explicitRoles.length > 0 ? explicitRoles : fallbackRole
  return mergedRoles.map((role) => normalizeRoleCode(role)).filter(Boolean)
}

export function hasAnyRole(user, requiredRoles = []) {
  const userRoles = getUserRoles(user)
  const normalizedRequiredRoles = requiredRoles.map((role) => normalizeRoleCode(role)).filter(Boolean)

  if (normalizedRequiredRoles.length === 0) {
    return false
  }

  return normalizedRequiredRoles.some((role) => userRoles.includes(role))
}
