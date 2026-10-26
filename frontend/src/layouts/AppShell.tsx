import {
  Image,
  LayoutDashboard,
  LayoutTemplate,
  LogOut,
  Menu,
  PenLine,
  ScrollText,
  Settings,
  UserRound,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { CompanyBrand } from '../components/common/CompanyBrand'
import { Avatar } from '../components/ui/Misc'
import { Spinner } from '../components/ui/Spinner'
import { useAuth } from '../hooks/useAuth'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

interface NavSection {
  title?: string
  items: NavItem[]
}

const ADMIN_NAV: NavSection[] = [
  { items: [{ to: '/admin/overview', label: 'Overview', icon: LayoutDashboard }] },
  {
    title: 'Manage',
    items: [
      { to: '/admin/employees', label: 'Employees', icon: Users },
      { to: '/admin/signatures', label: 'Signatures', icon: PenLine },
      { to: '/admin/banners', label: 'Banners', icon: Image },
      { to: '/admin/templates', label: 'Templates', icon: LayoutTemplate },
    ],
  },
  {
    title: 'Administration',
    items: [
      { to: '/admin/audit', label: 'Audit Logs', icon: ScrollText },
      { to: '/admin/settings', label: 'Settings', icon: Settings },
    ],
  },
]

const EMPLOYEE_NAV: NavSection[] = [
  {
    items: [
      { to: '/employee/signature', label: 'My Signature', icon: PenLine },
      { to: '/employee/profile', label: 'My Profile', icon: UserRound },
    ],
  },
]

const PAGE_TITLES: Record<string, string> = {
  overview: 'Overview',
  employees: 'Employees',
  signatures: 'Signatures',
  banners: 'Banners',
  templates: 'Templates',
  audit: 'Audit Logs',
  settings: 'Settings',
  signature: 'My Signature',
  profile: 'My Profile',
}

export function AppShell() {
  const { user, employee, logout } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  const nav = user?.role === 'ADMIN' ? ADMIN_NAV : EMPLOYEE_NAV
  const section = location.pathname.split('/')[2] ?? ''

  // Close the mobile drawer on navigation.
  useEffect(() => setOpen(false), [location.pathname])

  const displayName = employee?.full_name ?? (user?.role === 'ADMIN' ? 'Administrator' : user?.email ?? '')

  const sidebar = (
    <div className="flex h-full flex-col border-r border-slate-200 bg-surface">
      <div className="flex h-16 items-center justify-between gap-2 px-4">
        <CompanyBrand variant="sidebar" />
        <button
          type="button"
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden"
          onClick={() => setOpen(false)}
          aria-label="Close menu"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Main">
        {nav.map((group, i) => (
          <div key={group.title ?? i}>
            {group.title && (
              <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{group.title}</p>
            )}
            <div className="space-y-0.5">
              {group.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <span
                        className={`absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-brand-600 transition-opacity ${
                          isActive ? 'opacity-100' : 'opacity-0'
                        }`}
                        aria-hidden="true"
                      />
                      <Icon className={`h-[18px] w-[18px] ${isActive ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600'}`} />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-2">
          <Avatar name={displayName || 'User'} src={employee?.profile_photo_url} size={34} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-900">{displayName}</p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={async () => {
            setSigningOut(true)
            await logout()
          }}
          disabled={signingOut}
          className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:opacity-60"
        >
          {signingOut ? <Spinner className="h-[18px] w-[18px]" /> : <LogOut className="h-[18px] w-[18px] text-slate-400" />}
          Logout
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">{sidebar}</aside>

      {/* Tablet / mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} aria-hidden="true" />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-surface shadow-xl">{sidebar}</aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-slate-200 bg-surface/85 px-4 backdrop-blur sm:px-6 lg:px-8">
          {/* Thin accent line in the Casterly logo colours */}
          <span className="pointer-events-none absolute inset-x-0 top-0 h-[3px] bg-linear-to-r from-brand-600 via-brand-400 to-lime-accent" aria-hidden="true" />
          <button type="button" className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
          <div className="min-w-0 lg:hidden">
            <CompanyBrand variant="topbar" />
          </div>
          <p className="hidden text-sm text-slate-500 lg:block">
            <span className="text-slate-400">Signature Studio</span>
            {PAGE_TITLES[section] && (
              <>
                <span className="mx-2 text-slate-300">/</span>
                <span className="font-medium text-slate-700">{PAGE_TITLES[section]}</span>
              </>
            )}
          </p>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
