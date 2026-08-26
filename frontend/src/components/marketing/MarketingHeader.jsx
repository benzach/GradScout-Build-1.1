import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import Logo from './Logo'

const SECTION_LINKS = [
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#features', label: 'Features' },
  { href: '/#sources', label: 'Where we look' },
  { href: '/#faq', label: 'FAQ' },
]

export default function MarketingHeader() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { user } = useAuth()

  // Prevents the page scrolling behind the open mobile menu.
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [menuOpen])

  return (
    <header className="sticky top-0 z-50 bg-background/85 backdrop-blur-sm border-b border-primary-100">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between">
        <Logo size={30} wordmarkClassName="text-lg" />

        <nav className="hidden md:flex items-center gap-8" aria-label="Site">
          {SECTION_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-primary-600 hover:text-primary-900 transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <Link
              to="/app"
              className="text-sm font-semibold px-4 py-2 rounded-lg bg-accent-300 text-primary-900 hover:bg-accent-400 transition-colors"
            >
              Open GradScout
            </Link>
          ) : (
            <>
              <Link
                to="/app/login"
                className="text-sm font-medium text-primary-700 hover:text-primary-900 px-3 py-2 transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/app/login?mode=signup"
                className="text-sm font-semibold px-4 py-2 rounded-lg bg-accent-300 text-primary-900 hover:bg-accent-400 transition-colors"
              >
                Get started free
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() => setMenuOpen((o) => !o)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          className="md:hidden p-2 -mr-2 text-primary-800"
        >
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-primary-100 bg-background px-5 py-5">
          <nav className="flex flex-col gap-1" aria-label="Site">
            {SECTION_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMenuOpen(false)}
                className="text-[15px] font-medium text-primary-700 py-2.5"
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="flex flex-col gap-2 mt-4 pt-4 border-t border-primary-100">
            {user ? (
              <Link
                to="/app"
                className="text-center text-sm font-semibold px-4 py-2.5 rounded-lg bg-accent-300 text-primary-900"
              >
                Open GradScout
              </Link>
            ) : (
              <>
                <Link to="/app/login" className="text-center text-sm font-medium text-primary-700 py-2.5">
                  Sign in
                </Link>
                <Link
                  to="/app/login?mode=signup"
                  className="text-center text-sm font-semibold px-4 py-2.5 rounded-lg bg-accent-300 text-primary-900"
                >
                  Get started free
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
