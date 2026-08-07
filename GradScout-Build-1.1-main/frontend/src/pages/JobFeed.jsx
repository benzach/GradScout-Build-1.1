import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { timeAgo } from '../lib/time'

const PAGE_SIZE = 20

// Maps directly onto MatchStatus (backend/app/schemas.py) — "All" is the
// one case with no status param at all, so it's the only tab where a
// dismissed match still shows up (visually de-emphasized in JobCard
// below, rather than hidden, so "All" really does mean all).
const FILTERS = [
  { status: null, label: 'All' },
  { status: 'new', label: 'New' },
  { status: 'applied', label: 'Applied' },
  { status: 'dismissed', label: 'Dismissed' },
]

export default function JobFeed() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [filter, setFilter] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = useCallback(
    async (nextOffset, replace) => {
      replace ? setLoading(true) : setLoadingMore(true)
      setError('')
      try {
        const statusParam = filter ? `&status=${filter}` : ''
        const data = await api.get(`/feed?limit=${PAGE_SIZE}&offset=${nextOffset}${statusParam}`)
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
    [filter],
  )

  useEffect(() => {
    load(0, true)
  }, [load])

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
              key={f.label}
              onClick={() => setFilter(f.status)}
              className={`text-sm px-3 py-1.5 rounded-full border whitespace-nowrap transition-colors ${
                filter === f.status
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
              {filter === null
                ? 'No matches yet — check back soon, or widen your search criteria.'
                : 'Nothing here yet.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((match) => (
              <JobCard key={match.id} match={match} onOpen={() => navigate(`/jobs/${match.id}`)} />
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

function JobCard({ match, onOpen }) {
  const { job, status } = match
  const isDismissed = status === 'dismissed'
  const meta = [
    job.location_category || job.location,
    job.salary_text,
    job.contract_type,
    timeAgo(job.posted_date || job.first_seen_at),
  ].filter(Boolean)

  return (
    <button
      onClick={onOpen}
      className={`w-full bg-white rounded-2xl shadow-sm p-4 text-left hover:shadow-md transition-shadow ${
        isDismissed ? 'opacity-50' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className={`text-sm font-medium text-slate-900 truncate ${isDismissed ? 'line-through' : ''}`}>
            {job.title}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">{job.company}</p>
        </div>
        {status !== 'new' && (
          <span className="shrink-0 text-[10px] uppercase tracking-wide font-medium text-brand-700 bg-brand-50 px-2 py-0.5 rounded-full">
            {status}
          </span>
        )}
      </div>

      {meta.length > 0 && <p className="text-xs text-slate-400 mt-2">{meta.join(' · ')}</p>}

      {job.industry_category && (
        <span className="inline-block mt-2 text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
          {job.industry_category}
        </span>
      )}

      {job.sources.length > 1 && (
        <p className="text-[11px] text-slate-400 mt-2">Also found on {job.sources.length - 1} other site{job.sources.length > 2 ? 's' : ''}</p>
      )}
    </button>
  )
}
