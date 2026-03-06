import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
  TreeDeciduous,
  X,
} from 'lucide-react'

function isPathActive(pathname, to) {
  if (!to) {
    return false
  }

  return pathname === to || pathname.startsWith(`${to}/`)
}

function normalizeSearchText(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
}

function SidebarContent({
  modules,
  pathname,
  collapsed,
  expandedModuleId,
  searchQuery,
  onSelectModule,
  onNavigate,
}) {
  const normalizedQuery = normalizeSearchText(searchQuery)
  const isSearching = normalizedQuery.length > 0

  const filteredModules = useMemo(() => {
    if (!isSearching) {
      return modules
    }

    return modules
      .map((module) => {
        const moduleMatches = normalizeSearchText(module.label).includes(normalizedQuery)
        const children = Array.isArray(module.children) ? module.children : []

        if (moduleMatches) {
          return module
        }

        const matchedChildren = children.filter((child) =>
          normalizeSearchText(child.label).includes(normalizedQuery),
        )

        if (!matchedChildren.length) {
          return null
        }

        return {
          ...module,
          children: matchedChildren,
        }
      })
      .filter(Boolean)
  }, [isSearching, modules, normalizedQuery])

  const navOverflowClass = collapsed
    ? 'overflow-visible'
    : 'overflow-y-auto overflow-x-visible'

  return (
    <nav className={`mt-3 flex-1 space-y-1.5 px-3 pb-6 scrollbar-hide ${navOverflowClass}`}>
      {filteredModules.map((module) => {
        const Icon = module.icon || TreeDeciduous
        const hasChildren = module.children?.length > 0
        const isExpanded = isSearching ? true : expandedModuleId === module.id
        const moduleTarget = module.to || (hasChildren ? module.children[0].to : '#')
        const moduleIsActive = isPathActive(pathname, module.to) ||
          module.children?.some((item) => isPathActive(pathname, item.to))

        return (
          <div key={module.id} className="relative z-60 space-y-1">
            {hasChildren ? (
              collapsed ? (
                <div className="relative overflow-visible">
                  <button
                    type="button"
                    onClick={() => onSelectModule(module.id)}
                    className={[
                      'flex w-full min-w-0 items-center gap-3 rounded-xl px-4.5 py-2.5 text-sm font-bold tracking-tight transition-all duration-200',
                      moduleIsActive
                        ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
                        : isExpanded
                          ? 'bg-sidebar-accent text-sidebar-accent-foreground shadow-sm'
                        : 'text-primary hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                    ].join(' ')}
                    aria-expanded={isExpanded}
                    aria-label={`Abrir submenu ${module.label}`}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                  </button>

                  {isExpanded && (
                    <div className="absolute left-[calc(100%+0.5rem)] top-0 z-80 w-56 rounded-xl border border-sidebar-border bg-card p-2 text-sidebar-ring shadow-2xl">
                      <p className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {module.label}
                      </p>

                      <div className="space-y-1">
                        {module.children.map((item) => (
                          <NavLink
                            key={item.id}
                            to={item.to}
                            end
                            onClick={() => {
                              onNavigate?.()
                              onSelectModule(null)
                            }}
                            className={({ isActive }) =>
                              [
                                'flex items-center gap-2 rounded-lg border px-2.5 py-2 text-sm font-semibold transition-all',
                                isActive
                                  ? 'border-sidebar-primary bg-sidebar-primary text-sidebar-primary-foreground'
                                  : 'border-sidebar-border bg-card text-sidebar-ring hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                              ].join(' ')
                            }
                          >
                            <ChevronRight className="h-3.5 w-3.5" />
                            <span className="truncate">{item.label}</span>
                          </NavLink>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => onSelectModule(module.id)}
                  className={[
                    'flex w-full min-w-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition-all duration-200',
                    moduleIsActive
                      ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
                      : 'text-primary hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  ].join(' ')}
                >
                  <Icon className="h-5 w-5 shrink-0" />
                  <span className="min-w-0 flex-1 truncate pr-1 text-left leading-5">
                    {module.label}
                  </span>

                  <ChevronDown
                    className={[
                      'ml-auto h-4 w-4 transition-transform duration-300',
                      isExpanded ? 'rotate-180' : '',
                    ].join(' ')}
                  />
                </button>
              )
            ) : (
              <NavLink
                to={moduleTarget}
                end
                onClick={onNavigate}
                className={({ isActive }) =>
                  [
                    'flex w-full min-w-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold transition-all duration-200',
                    isActive
                      ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
                      : 'text-primary hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  ].join(' ')
                }
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && (
                  <span className="min-w-0 flex-1 truncate pr-1 leading-5">{module.label}</span>
                )}
              </NavLink>
            )}

            {!collapsed && hasChildren && isExpanded && (
              <div className="mt-1 ml-4 space-y-1 border-l-2 border-sidebar-border pl-3">
                {module.children.map((item) => (
                  <NavLink
                    key={item.id}
                    to={item.to}
                    end
                    onClick={() => {
                      onNavigate?.()
                      onSelectModule(null)
                    }}
                    className={({ isActive }) =>
                      [
                        'flex items-center gap-3 rounded-lg border px-3 py-2 text-[13px] font-semibold transition-all',
                        isActive
                          ? 'border-sidebar-primary bg-sidebar-primary text-sidebar-primary-foreground'
                          : 'border-sidebar-border bg-card text-sidebar-ring hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                      ].join(' ')
                    }
                  >
                    <span>{item.label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        )
      })}

      {!filteredModules.length && !collapsed && (
        <div className="rounded-xl border border-dashed border-sidebar-border bg-card/70 px-3 py-4 text-center text-xs font-semibold text-muted-foreground">
          No se encontraron menus para "{searchQuery}".
        </div>
      )}
    </nav>
  )
}

function Sidebar({
  modules,
  collapsed,
  mobileOpen,
  onCloseMobile,
  onToggleCollapsed,
}) {
  const location = useLocation()
  const desktopSidebarRef = useRef(null)
  const desktopSearchInputRef = useRef(null)
  const mobileSearchInputRef = useRef(null)
  const [manuallyExpandedModuleId, setManuallyExpandedModuleId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const expandedModuleId = manuallyExpandedModuleId
  const effectiveSearchQuery = collapsed ? '' : searchQuery

  useEffect(() => {
    if (!collapsed || !expandedModuleId) {
      return undefined
    }

    const handleClickOutside = (event) => {
      if (!desktopSidebarRef.current) {
        return
      }

      if (desktopSidebarRef.current.contains(event.target)) {
        return
      }

      setManuallyExpandedModuleId(null)
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setManuallyExpandedModuleId(null)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [collapsed, expandedModuleId])

  const handleSelectModule = (moduleId) => {
    if (collapsed) {
      setManuallyExpandedModuleId((prev) => (prev === moduleId ? null : moduleId))
      return
    }

    if (!moduleId) {
      setManuallyExpandedModuleId(null)
      return
    }

    setManuallyExpandedModuleId((prev) => (prev === moduleId ? null : moduleId))
  }

  const desktopWidthClass = collapsed ? 'w-[84px]' : 'w-[260px]'

  return (
    <>
      <aside
        ref={desktopSidebarRef}
        className={[
          'fixed bottom-0 left-0 top-16 z-70 hidden border-r border-sidebar-border bg-muted shadow-xl transition-all duration-500 ease-in-out lg:flex lg:flex-col',
          desktopWidthClass,
        ].join(' ')}
      >
        <div
          className={[
            'flex h-12 items-center border-b border-t border-sidebar-border px-3',
            collapsed ? 'justify-center' : 'justify-between',
          ].join(' ')}
        >
          {!collapsed && (
            <label className="relative mr-2 flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                ref={desktopSearchInputRef}
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Buscar menu"
                className="h-8 w-full rounded-md border border-sidebar-border bg-card pl-8 pr-8 text-xs text-primary outline-none transition-colors placeholder:text-muted-foreground focus:border-sidebar-primary"
              />

              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('')
                    desktopSearchInputRef.current?.focus()
                  }}
                  className="absolute right-1.5 top-1/2 inline-flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  aria-label="Limpiar busqueda"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </label>
          )}

          <button
            type="button"
            onClick={onToggleCollapsed}
            className="inline-flex rounded-md p-2 text-primary/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            aria-label={collapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
          >
            {collapsed ? (
              <PanelLeftOpen className="h-5 w-5" />
            ) : (
              <PanelLeftClose className="h-5 w-5" />
            )}
          </button>
        </div>

        <SidebarContent
          modules={modules}
          pathname={location.pathname}
          collapsed={collapsed}
          expandedModuleId={expandedModuleId}
          searchQuery={effectiveSearchQuery}
          onSelectModule={handleSelectModule}
          onNavigate={() => {}}
        />
        
        {!collapsed && (
          <div className="border-t border-sidebar-border p-6">
            <div className="flex items-center gap-3 text-primary/70">
              <ShieldCheck size={16} />
              <span className="text-[10px] font-black uppercase tracking-[0.2em]">ELDANOR SOFTWARE</span>
            </div>
          </div>
        )}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-foreground/35 backdrop-blur-sm lg:hidden" onClick={onCloseMobile} />
      )}

      <aside
        className={[
          'fixed inset-y-0 left-0 z-50 w-72 border-r border-sidebar-border bg-muted transition-transform duration-500 ease-out lg:hidden',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-3">
          <label className="relative flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              ref={mobileSearchInputRef}
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Buscar menu"
              className="h-8 w-full rounded-md border border-sidebar-border bg-card pl-8 pr-8 text-xs text-primary outline-none transition-colors placeholder:text-muted-foreground focus:border-sidebar-primary"
            />

            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('')
                  mobileSearchInputRef.current?.focus()
                }}
                className="absolute right-1.5 top-1/2 inline-flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                aria-label="Limpiar busqueda"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </label>

          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-full p-2 text-primary/75 hover:bg-sidebar-accent"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <SidebarContent
          modules={modules}
          pathname={location.pathname}
          collapsed={false}
          expandedModuleId={expandedModuleId}
          searchQuery={effectiveSearchQuery}
          onSelectModule={handleSelectModule}
          onNavigate={onCloseMobile}
        />
      </aside>
    </>
  )
}

export default Sidebar