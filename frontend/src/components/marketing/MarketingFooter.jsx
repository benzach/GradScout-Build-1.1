import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function MarketingFooter() {
  return (
    <footer className="border-t border-primary-100 bg-background">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 py-12">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-10">
          <div className="max-w-xs">
            <Logo size={28} wordmarkClassName="text-base" />
            <p className="text-sm text-primary-500 mt-3 leading-relaxed">
              One search, run continuously across the UK's graduate job boards — deduplicated,
              matched, and sent straight to you.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:gap-16">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-primary-400 mb-3">Product</p>
              <ul className="space-y-2.5 text-sm">
                <li>
                  <a href="/#how-it-works" className="text-primary-600 hover:text-primary-900 transition-colors">
                    How it works
                  </a>
                </li>
                <li>
                  <a href="/#features" className="text-primary-600 hover:text-primary-900 transition-colors">
                    Features
                  </a>
                </li>
                <li>
                  <a href="/#faq" className="text-primary-600 hover:text-primary-900 transition-colors">
                    FAQ
                  </a>
                </li>
                <li>
                  <Link to="/app/login" className="text-primary-600 hover:text-primary-900 transition-colors">
                    Sign in
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-primary-400 mb-3">Legal</p>
              <ul className="space-y-2.5 text-sm">
                <li>
                  <Link to="/terms" className="text-primary-600 hover:text-primary-900 transition-colors">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link to="/privacy" className="text-primary-600 hover:text-primary-900 transition-colors">
                    Privacy Notice
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-primary-100 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
          <p className="text-xs text-primary-400">© {new Date().getFullYear()} GradScout. All job listings remain the property of the site that published them.</p>
          <p className="text-xs text-primary-400">Built in the UK, for UK graduates.</p>
        </div>
      </div>
    </footer>
  )
}
