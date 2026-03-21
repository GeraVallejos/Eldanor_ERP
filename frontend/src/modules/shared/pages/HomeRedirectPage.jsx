import { Navigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { selectCurrentUser } from '@/modules/auth/authSlice'
import { resolveNavigation } from '@/config/navigation'

function HomeRedirectPage() {
  const user = useSelector(selectCurrentUser)
  const firstAvailableRoute = resolveNavigation(user)
    .flatMap((module) => module.children || [])
    .find((item) => item.to)?.to

  if (firstAvailableRoute) {
    return <Navigate to={firstAvailableRoute} replace />
  }

  return (
    <section className="rounded-xl border border-border bg-card p-6">
      <h2 className="text-xl font-semibold">Sin modulos disponibles</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Su usuario no tiene permisos visibles para navegar el ERP actual.
      </p>
    </section>
  )
}

export default HomeRedirectPage
