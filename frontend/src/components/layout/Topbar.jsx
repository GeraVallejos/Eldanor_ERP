import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Building2,
  Check,
  ChevronsUpDown,
  LoaderCircle,
  LogOut,
  Menu,
  UserCircle2,
} from 'lucide-react'

function Topbar({
  user,
  empresas,
  empresasStatus,
  changingEmpresaId,
  onOpenMobileMenu,
  onChangeEmpresa,
  onLogout,
}) {
  const companyName = user?.empresa_nombre || 'Mi Empresa'
  const companyLogoUrl = user?.empresa_logo || null
  const userDisplayName = user?.username || user?.email || 'sin identificar'
  const [logoState, setLogoState] = useState({
    url: null,
    loaded: false,
    error: false,
  })
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const empresasDisponibles = useMemo(
    () => (Array.isArray(empresas) ? empresas : []),
    [empresas],
  )
  const canSwitchEmpresas = empresasDisponibles.length > 1

  const empresaActivaId = useMemo(() => {
    if (user?.empresa_id) {
      return String(user.empresa_id)
    }

    const activa = empresasDisponibles.find((empresa) => empresa?.es_activa)
    return activa ? String(activa.id) : null
  }, [empresasDisponibles, user])

  useEffect(() => {
    if (!menuOpen) {
      return undefined
    }

    const handleClickOutside = (event) => {
      if (!menuRef.current || menuRef.current.contains(event.target)) {
        return
      }

      setMenuOpen(false)
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [menuOpen])

  const isCurrentLogoLoaded =
    logoState.url === companyLogoUrl && logoState.loaded
  const isCurrentLogoErrored =
    logoState.url === companyLogoUrl && logoState.error
  const showLogo = Boolean(companyLogoUrl && !isCurrentLogoErrored)

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-sidebar-border bg-muted backdrop-blur">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenMobileMenu}
            className="rounded-md p-2 hover:bg-muted lg:hidden"
            aria-label="Abrir menu lateral"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg border border-border bg-card">
              {showLogo ? (
                <>
                  {!isCurrentLogoLoaded && (
                    <LoaderCircle className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                  <img
                    key={companyLogoUrl}
                    src={companyLogoUrl}
                    alt={`Logo ${companyName}`}
                    className={[
                      'h-full w-full object-cover',
                      isCurrentLogoLoaded ? 'block' : 'hidden',
                    ].join(' ')}
                    onLoad={() =>
                      setLogoState({
                        url: companyLogoUrl,
                        loaded: true,
                        error: false,
                      })
                    }
                    onError={() =>
                      setLogoState({
                        url: companyLogoUrl,
                        loaded: false,
                        error: true,
                      })
                    }
                  />
                </>
              ) : (
                <Building2 className="h-4 w-4 text-muted-foreground" />
              )}
            </div>

            <div>
              <h1 className="text-sm font-semibold sm:text-base text-primary">{companyName}</h1>
              <p className="text-xs text-sidebar-foreground/55">Panel Operativo</p>
            </div>
          </div>
        </div>

        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((prev) => !prev)}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-muted"
            aria-expanded={menuOpen}
            aria-haspopup="menu"
          >
            <UserCircle2 className="h-4 w-4 text-chart-2" />
            <span className="max-w-40 truncate text-primary font-bold">{userDisplayName}</span>
            <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 z-50 mt-2 w-72 rounded-xl border border-border bg-popover p-2 shadow-lg">
              <div className="rounded-lg px-2 py-2">
                <p className="text-sm font-semibold">{userDisplayName}</p>
                <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
                <p className="mt-1 truncate text-xs text-muted-foreground">Empresa activa: {companyName}</p>
              </div>

              {canSwitchEmpresas && (
                <div className="mt-1 border-t border-border pt-2">
                  <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Cambiar empresa
                  </p>

                  <div className="space-y-1">
                    {empresasDisponibles.map((empresa) => {
                      const empresaId = String(empresa.id)
                      const isActive = empresaId === empresaActivaId
                      const isLoading = changingEmpresaId ? String(changingEmpresaId) === empresaId : false

                      return (
                        <button
                          key={empresa.id}
                          type="button"
                          onClick={() => {
                            if (!isActive && !isLoading) {
                              onChangeEmpresa?.(empresa.id)
                            }
                            setMenuOpen(false)
                          }}
                          disabled={isActive || isLoading || empresasStatus === 'loading'}
                          className={[
                            'flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-sm transition-colors',
                            isActive
                              ? 'bg-accent text-accent-foreground'
                              : 'hover:bg-muted',
                            isLoading ? 'opacity-70' : '',
                          ].join(' ')}
                        >
                          <span className="truncate">{empresa.nombre}</span>
                          {isLoading ? (
                            <LoaderCircle className="h-4 w-4 animate-spin" />
                          ) : isActive ? (
                            <Check className="h-4 w-4" />
                          ) : null}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}

              <div className="mt-2 border-t border-border pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false)
                    onLogout()
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm text-destructive transition-colors hover:bg-destructive/10"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Cerrar sesion</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Topbar