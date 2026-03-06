import { useSelector } from 'react-redux'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import {
  selectAuthBootstrapStatus,
  selectIsAuthenticated,
} from '@/modules/auth/authSlice'

function PrivateRoute() {
  const location = useLocation()
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const bootstrapStatus = useSelector(selectAuthBootstrapStatus)

  if (bootstrapStatus === 'idle' || bootstrapStatus === 'loading') {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export default PrivateRoute
