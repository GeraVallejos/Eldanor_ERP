import { useMemo } from 'react'
import { useSelector } from 'react-redux'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import { hasAnyPermission, hasPermission } from '@/modules/shared/auth/permissions'

function PermissionRoute({ permission, message, children, requireAny = false }) {
  const user = useSelector(selectCurrentUser)
  const canAccess = useMemo(() => {
    if (Array.isArray(permission)) {
      return requireAny ? hasAnyPermission(user, permission) : permission.every((code) => hasPermission(user, code))
    }
    return hasPermission(user, permission)
  }, [requireAny, user, permission])

  if (!canAccess) {
    return (
      <p className="text-sm text-destructive">
        {message || 'No tiene permiso para acceder a este modulo.'}
      </p>
    )
  }

  return children
}

export default PermissionRoute
