import { useMemo } from 'react'
import { useSelector } from 'react-redux'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import { hasPermission } from '@/modules/shared/auth/permissions'

function PermissionRoute({ permission, message, children }) {
  const user = useSelector(selectCurrentUser)
  const canAccess = useMemo(() => hasPermission(user, permission), [user, permission])

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
