import MarketingHeader from './MarketingHeader'
import MarketingFooter from './MarketingFooter'

/**
 * Shared chrome for every public, unauthenticated page (Landing, plus
 * Terms/Privacy so they read as part of one site rather than orphaned
 * standalone screens when someone lands directly on /privacy from a
 * search engine). The actual product (everything under /app) keeps its
 * own mobile app chrome — BackButton/BottomNav — instead of this.
 */
export default function MarketingLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <MarketingHeader />
      <main className="flex-1">{children}</main>
      <MarketingFooter />
    </div>
  )
}
