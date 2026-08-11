import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star } from 'lucide-react'
import { api } from '../lib/api'
import { timeAgo } from '../lib/time'

const PAGE_SIZE = 20

// Each tab maps to a distinct combination of query params sent to
// GET /feed. "Favourites" and "status" are independent filters on the
// backend (see app/models.py's UserJobMatch.is_favourite) — a
// dismissed job can still be a favourite — but the tabs themselves
// stay mutually exclusive here, since showing two active filters at
// once in this small a UI would be more confusing than useful.
const FILTERS = [
  { key: 'all', label: 'All', status: null, favouritesOnly: false },
  { key: 'new', label: 'New', status: 'new', favouritesOnly: false },
  { key: 'applied', label: 'Applied', status: 'applied', favouritesOnly: false },
  { key: 'dismissed', label: 'Dismissed', status: 'dismissed', favouritesOnly: false },
  { key: 'favourites', label: '★ Favourites', status: null, favouritesOnly: true },
]

export default function JobFeed() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [activeFilter, setActiveFilter] = useState(FILTERS[0])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = useCallback(
    async (nextOffset, replace) => {
      replace ? setLoading(true) : setLoadingMore(true)
      setError('')
      try {
        const params = new URLSearchParams({ limit: PAGE_SIZE, offset: nextOffset })
        if (activeFilter.status) params.set('status', activeFilter.status)
        if (activeFilter.favouritesOnly) params.set('favourites_only', 'true')

        const data = await api.get(`/feed?${params}`)
        setItems((prev) => (replace ? data.items : [...prev, ...data.items]))
        setTotal(data.total)
        setOffset(nextOffset)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    },
    [activeFilter],
  )

  useEffect(() => {
    load(0, true)
  }, [load])

  function handleToggleFavourite(matchId, nextValue) {
    // Optimistic update — a favourite toggle should feel instant, and
    // a failure here is rare enough (and low-stakes enough) that
    // rolling back on error is simpler and more honest than pretending
    // this needs a loading spinner.
    setItems((prev) => prev.map((m) => (m.id === matchId ? { ...m, is_favourite: nextValue } : m)))
    api.patch(`/matches/${matchId}`, { is_favourite: nextValue }).catch(() => {
      setItems((prev) => prev.map((m) => (m.id === matchId ? { ...m, is_favourite: !nextValue } : m)))
      setError('Could not update that — please try again.')
    })
  }

  const hasMore = offset + PAGE_SIZE < total

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="max-w-sm mx-auto">
        <button onClick={() => navigate('/')} className="text-sm text-slate-500 hover:text-slate-700 mb-4">
          ← Back
        </button>

        <h1 className="text-lg font-semibold text-slate-900 mb-1">Your matches</h1>
        <p className="text-sm text-slate-500 mb-4">Jobs matching your saved searches, newest first.</p>

        <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setActiveFilter(f)}
              className={`text-sm px-3 py-1.5 rounded-full border whitespace-nowrap transition-colors ${
                activeFilter.key === f.key
                  ? 'bg-brand-950 border-brand-950 text-white'
                  : 'bg-white border-slate-200 text-slate-600'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-4">{error}</p>}

        {loading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm p-6 text-center">
            <p className="text-sm text-slate-500">
              {activeFilter.key === 'all'
                ? 'No matches yet — check back soon, or widen your search criteria.'
                : activeFilter.key === 'favourites'
                  ? "You haven't favourited anything yet."
                  : 'Nothing here yet.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((match) => (
              <JobCard
                key={match.id}
                match={match}
                onOpen={() => navigate(`/jobs/${match.id}`)}
                onToggleFavourite={(next) => handleToggleFavourite(match.id, next)}
              />
            ))}
          </div>
        )}

        {hasMore && !loading && (
          <button
            onClick={() => load(offset + PAGE_SIZE, false)}
            disabled={loadingMore}
            className="w-full mt-4 py-2.5 rounded-lg border border-slate-200 text-sm font-medium text-slate-600 bg-white hover:bg-slate-50 transition-colors disabled:opacity-50"
          >
            {loadingMore ? 'Loading…' : 'Load more'}
          </button>
        )}
      </div>
    </div>
  )
}

function JobCard({ match, onOpen, onToggleFavourite }) {
  const { job, status, is_favourite: isFavourite } = match
  const isDismissed = status === 'dismissed'
  const meta = [
    job.location_category || job.location,
    job.salary_text,
    job.contract_type,
    timeAgo(job.posted_date || job.first_seen_at),
  ].filter(Boolean)

  // A <div role="button"> rather than a real <button> for the outer
  // card, since it needs to contain the favourite toggle's own real
  // <button> — nesting interactive elements is invalid HTML, and two
  // browsers will actually handle a nested button/button click
  // differently, not just look wrong.
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onOpen()}
      className={`w-full bg-white rounded-2xl shadow-sm p-4 text-left hover:shadow-md transition-shadow cursor-pointer ${
        isDismissed ? 'opacity-50' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className={`text-sm font-medium text-slate-900 truncate ${isDismissed ? 'line-through' : ''}`}>
            {job.title}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">{job.company}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {status !== 'new' && (
            <span className="text-[10px] uppercase tracking-wide font-medium text-brand-700 bg-brand-50 px-2 py-0.5 rounded-full">
              {status}
            </span>
          )}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onToggleFavourite(!isFavourite)
            }}
            aria-label={isFavourite ? 'Remove from favourites' : 'Add to favourites'}
            aria-pressed={isFavourite}
            className="p-1 -m-1 text-slate-300 hover:text-brand-500 transition-colors"
          >
            <Star size={18} fill={isFavourite ? 'currentColor' : 'none'} className={isFavourite ? 'text-brand-500' : ''} />
          </button>
        </div>
      </div>

      {meta.length > 0 && <p className="text-xs text-slate-400 mt-2">{meta.join(' · ')}</p>}

      {job.industry_category && (
        <span className="inline-block mt-2 text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
          {job.industry_category}
        </span>
      )}

      {job.sources.length > 1 && (
        <p className="text-[11px] text-slate-400 mt-2">
          Also found on {job.sources.length - 1} other site{job.sources.length > 2 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
