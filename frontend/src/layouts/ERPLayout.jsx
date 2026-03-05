import { useDispatch, useSelector } from 'react-redux'
import { NavLink, Outlet } from 'react-router-dom'
import { logout, selectCurrentUser } from '@/modules/auth/authSlice'
import { clearStoredSession } from '@/modules/auth/utils/tokenStorage'

const links = [
  { to: '/productos', label: 'Productos' },
  { to: '/productos/nuevo', label: 'Nuevo producto' },
  { to: '/contactos', label: 'Contactos' },
  { to: '/presupuestos', label: 'Presupuestos' },
]

function ERPLayout() {
  const dispatch = useDispatch()
  const user = useSelector(selectCurrentUser)

  const handleLogout = () => {
    clearStoredSession()
    dispatch(logout())
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
          <div>
            <h1 className="text-lg font-semibold">Eldanor ERP</h1>
            <p className="text-xs text-muted-foreground">
              Usuario: {user?.username || 'sin identificar'}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-2">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    [
                      'rounded-md px-3 py-1.5 text-sm transition-colors',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'hover:bg-muted',
                    ].join(' ')
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}

export default ERPLayout
