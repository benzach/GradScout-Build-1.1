import { NavLink } from 'react-router-dom'
import { Home, Briefcase, Settings as SettingsIcon } from 'lucide-react'

const TABS = [
  { to: '/app', label: 'Home', icon: Home, end: true },
  { to: '/app/feed', label: 'Matches', icon: Briefcase },
  { to: '/app/settings', label: 'Settings', icon: SettingsIcon },
]

/**
 * Fixed bottom tab bar for the app's three top-level sections. Rendered
 * on Home, JobFeed, and Settings only — Criteria, JobDetail, Login, and
 * Privacy are reached by drilling in (and use BackButton to return),
 * the same split most mobile apps make between "tab root" screens and
 * "pushed" screens.
 */
export default function BottomNav() {
  return (
    <nav
      className="fixed bottom-0 inset-x-0 z-40 bg-white border-t border-primary-100 pb-[env(safe-area-inset-bottom)]"
      aria-label="Primary"
    >
      <div className="max-w-sm mx-auto grid grid-cols-3">
        {TABS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 py-2.5 text-xs font-medium transition-colors ${
                isActive ? 'text-primary-900' : 'text-primary-400'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 2} className={isActive ? 'text-accent-400' : ''} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
