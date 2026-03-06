import { useSelector } from 'react-redux'
import { Navigate, Outlet } from 'react-router-dom'
import {
  selectAuthBootstrapStatus,
  selectIsAuthenticated,
} from '@/modules/auth/authSlice'

function PublicOnlyRoute() {
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const bootstrapStatus = useSelector(selectAuthBootstrapStatus)

  if (bootstrapStatus === 'idle' || bootstrapStatus === 'loading') {
    return null
  }

  if (isAuthenticated) {
    return <Navigate to="/productos" replace />
  }

  return <Outlet />
}

export default PublicOnlyRoute
