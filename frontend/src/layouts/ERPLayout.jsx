import { useEffect, useMemo, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Outlet } from 'react-router-dom'
import Sidebar from '@/components/layout/Sidebar'
import Topbar from '@/components/layout/Topbar'
import { resolveNavigation } from '@/config/navigation'
import {
  changeEmpresaActiva,
  fetchEmpresasUsuario,
  logoutUser,
  selectChangingEmpresaId,
  selectCurrentUser,
  selectEmpresasStatus,
  selectEmpresasUsuario,
} from '@/modules/auth/authSlice'

function ERPLayout() {
  const dispatch = useDispatch()
  const user = useSelector(selectCurrentUser)
  const empresas = useSelector(selectEmpresasUsuario)
  const empresasStatus = useSelector(selectEmpresasStatus)
  const changingEmpresaId = useSelector(selectChangingEmpresaId)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  const modules = useMemo(() => resolveNavigation(user), [user])

  useEffect(() => {
    if (!user) {
      return
    }

    dispatch(fetchEmpresasUsuario())
  }, [dispatch, user])

  const handleLogout = () => {
    sessionStorage.setItem('auth:manualLogout', '1')
    dispatch(logoutUser())
  }

  const handleChangeEmpresa = (empresaId) => {
    if (!empresaId) {
      return
    }

    dispatch(changeEmpresaActiva(empresaId))
  }

  const contentPaddingClass = sidebarCollapsed ? 'lg:pl-[84px]' : 'lg:pl-[260px]'

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Topbar
        user={user}
        empresas={empresas}
        empresasStatus={empresasStatus}
        changingEmpresaId={changingEmpresaId}
        onOpenMobileMenu={() => setMobileSidebarOpen(true)}
        onChangeEmpresa={handleChangeEmpresa}
        onLogout={handleLogout}
      />

      <Sidebar
        modules={modules}
        collapsed={sidebarCollapsed}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        onToggleCollapsed={() => setSidebarCollapsed((prev) => !prev)}
      />

      <div className={`${contentPaddingClass} pt-16`}>
        <main className="px-4 py-6 sm:px-6 lg:px-8">
          <section className="rounded-2xl border border-border bg-card p-4 text-card-foreground shadow-sm sm:p-6">
            <Outlet />
          </section>
        </main>
      </div>
    </div>
  )
}

export default ERPLayout
