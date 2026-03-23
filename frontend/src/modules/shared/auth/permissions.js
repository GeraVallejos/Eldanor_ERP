function normalizePermissionCode(code) {
  return String(code || '').trim().toUpperCase()
}

export function hasPermission(user, permissionCode) {
  const target = normalizePermissionCode(permissionCode)
  if (!target) {
    return false
  }

  const permissions = Array.isArray(user?.permissions)
    ? user.permissions.map((permission) => normalizePermissionCode(permission))
    : []

  if (permissions.includes('*')) {
    return true
  }

  if (permissions.includes(target)) {
    return true
  }

  const [moduleCode] = target.split('.')
  if (!moduleCode) {
    return false
  }

  return permissions.includes(`${moduleCode}.*`)
}

export function hasAnyPermission(user, permissionCodes = []) {
  if (!Array.isArray(permissionCodes) || permissionCodes.length === 0) {
    return false
  }

  return permissionCodes.some((permissionCode) => hasPermission(user, permissionCode))
}

export function canManagePresupuestoStatus(user, currentStatus, targetStatus) {
  const from = String(currentStatus || '').toUpperCase()
  const to = String(targetStatus || '').toUpperCase()

  if (!from || !to || from === to) {
    return false
  }

  if (to === 'APROBADO') {
    return hasPermission(user, 'PRESUPUESTOS.APROBAR')
  }

  if (to === 'ANULADO') {
    return hasPermission(user, 'PRESUPUESTOS.ANULAR')
  }

  return hasPermission(user, 'PRESUPUESTOS.EDITAR')
}
