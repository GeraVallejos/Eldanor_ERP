import { useSelector } from 'react-redux'
import { Navigate, Outlet } from 'react-router-dom'
import { selectIsAuthenticated } from '@/modules/auth/authSlice'

function PublicOnlyRoute() {
  const isAuthenticated = useSelector(selectIsAuthenticated)

  if (isAuthenticated) {
    return <Navigate to="/productos" replace />
  }

  return <Outlet />
}

export default PublicOnlyRoute
