import { useMemo } from 'react'
import { useSelector } from 'react-redux'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import { hasPermission } from '@/modules/shared/auth/permissions'

export function usePermission(permissionCode) {
  const user = useSelector(selectCurrentUser)
  return useMemo(() => hasPermission(user, permissionCode), [user, permissionCode])
}

export function usePermissions(permissionCodes = []) {
  const user = useSelector(selectCurrentUser)
  return useMemo(() => {
    return permissionCodes.reduce((acc, code) => {
      acc[code] = hasPermission(user, code)
      return acc
    }, {})
  }, [user, permissionCodes])
}
