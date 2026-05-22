import { NavLink, Link } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Home', end: true },
  { to: '/pricing', label: 'Pricing' },
  { to: '/install', label: 'Install' },
  { to: '/sync', label: 'Sync' },
  { to: '/docs', label: 'Docs' },
  { to: '/changelog', label: 'Changelog' },
]

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/70">
      <div className="container-wide flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <span
            aria-hidden
            className="flex h-8 w-8 items-center justify-center rounded-xl bg-sidebar text-sidebar-foreground"
          >
            R
          </span>
          <span>Research Assistant</span>
        </Link>
        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive ? 'bg-slate-100 text-ink' : 'text-ink-muted hover:bg-slate-50 hover:text-ink',
                ].join(' ')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            to="/login"
            className="hidden text-sm font-medium text-ink-muted hover:text-ink sm:inline-flex sm:px-3 sm:py-2"
          >
            Sign in
          </Link>
          <Link to="/signup" className="btn-primary !px-4 !py-2 text-xs sm:text-sm">
            Start free trial
          </Link>
        </div>
      </div>
    </header>
  )
}
