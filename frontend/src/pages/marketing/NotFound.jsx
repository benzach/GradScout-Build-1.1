import { Link } from 'react-router-dom'
import MarketingLayout from '../../components/marketing/MarketingLayout'

export default function NotFound() {
  return (
    <MarketingLayout>
      <div className="max-w-md mx-auto px-5 py-24 text-center">
        <p className="font-heading text-sm font-bold tracking-widest text-accent-400 mb-3">404</p>
        <h1 className="font-heading text-3xl font-extrabold text-primary-900">
          That page has moved on
        </h1>
        <p className="text-primary-600 mt-3 leading-relaxed">
          Maybe it dismissed itself, maybe it never existed — either way, there's nothing at this
          address. Try the homepage, or head straight into your feed.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center mt-8">
          <Link
            to="/"
            className="px-5 py-2.5 rounded-lg border border-primary-200 text-sm font-semibold text-primary-700 hover:bg-primary-50 transition-colors"
          >
            Back to homepage
          </Link>
          <Link
            to="/app"
            className="px-5 py-2.5 rounded-lg bg-accent-300 text-sm font-semibold text-primary-900 hover:bg-accent-400 transition-colors"
          >
            Open GradScout
          </Link>
        </div>
      </div>
    </MarketingLayout>
  )
}
