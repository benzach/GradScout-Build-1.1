import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Star } from 'lucide-react'
import { api } from '../lib/api'

const STATUS_ACTIONS = [
  { status: 'seen', label: 'Mark as seen' },
  { status: 'applied', label: "I've applied" },
  { status: 'dismissed', label: 'Not interested' },
]

export default function JobDetail() {
  const { matchId } = useParams()
  const navigate = useNavigate()
  const [match, setMatch] = useState(null)
  const [error, setError] = useState('')
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    // There's no GET /matches/{id} — the feed is the only listing
    // endpoint today, so the specific match is pulled out of a feed
    // page rather than adding a new backend route just for this one
    // screen. Fine at 21-tester scale; worth a dedicated endpoint if
    // any one user's realistic match count ever outgrows a page or two.
    api
      .get('/feed?limit=100')
      .then((data) => {
        const found = data.items.find((m) => m.id === matchId)
        if (found) setMatch(found)
        else setError('Could not find that match — it may have changed.')
      })
      .catch((e) => setError(e.message))
  }, [matchId])

  async function updateStatus(status) {
    setUpdating(true)
    setError('')
    try {
      const updated = await api.patch(`/matches/${matchId}`, { status })
      setMatch(updated)
    } catch (e) {
      setError(e.message)
    } finally {
      setUpdating(false)
    }
  }

  async function toggleFavourite() {
    const nextValue = !match.is_favourite
    setMatch((prev) => ({ ...prev, is_favourite: nextValue })) // optimistic — same reasoning as JobFeed.jsx's card toggle
    try {
      const updated = await api.patch(`/matches/${matchId}`, { is_favourite: nextValue })
      setMatch(updated)
    } catch (e) {
      setMatch((prev) => ({ ...prev, is_favourite: !nextValue }))
      setError(e.message)
    }
  }

  if (!match && !error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-sm text-slate-400">Loading…</p>
      </div>
    )
  }

  if (error && !match) {
    return (
      <div className="min-h-screen bg-slate-50 px-4 py-8">
        <div className="max-w-sm mx-auto">
          <button onClick={() => navigate('/feed')} className="text-sm text-slate-500 hover:text-slate-700 mb-4">
            ← Back
          </button>
          <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>
        </div>
      </div>
    )
  }

  const { job, status, is_favourite: isFavourite } = match
  const tags = [job.location_category || job.location, job.contract_type, job.remote_type].filter(Boolean)

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="max-w-sm mx-auto">
        <button onClick={() => navigate('/feed')} className="text-sm text-slate-500 hover:text-slate-700 mb-4">
          ← Back
        </button>

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-lg font-semibold text-slate-900">{job.title}</h1>
              <p className="text-sm text-slate-500 mt-0.5">{job.company}</p>
            </div>
            <button
              type="button"
              onClick={toggleFavourite}
              aria-label={isFavourite ? 'Remove from favourites' : 'Add to favourites'}
              aria-pressed={isFavourite}
              className="p-1.5 -m-1.5 text-slate-300 hover:text-brand-500 transition-colors shrink-0"
            >
              <Star size={22} fill={isFavourite ? 'currentColor' : 'none'} className={isFavourite ? 'text-brand-500' : ''} />
            </button>
          </div>

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {tags.map((tag) => (
                <span key={tag} className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {job.salary_text && <p className="text-sm text-slate-700 font-medium mt-3">{job.salary_text}</p>}

          {job.description && (
            <p className="text-sm text-slate-600 mt-4 whitespace-pre-line leading-relaxed">{job.description}</p>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-4">
          <p className="text-sm font-medium text-slate-900 mb-3">
            Found on {job.sources.length} {job.sources.length === 1 ? 'site' : 'sites'}
          </p>
          <div className="space-y-2">
            {job.sources.map((src) => (
              <a
                key={src.source_url}
                href={src.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between text-sm px-3 py-2.5 rounded-lg border border-slate-200 hover:border-brand-500 transition-colors"
              >
                <span className="text-slate-700 capitalize">{src.site}</span>
                <span className="text-brand-600">View original →</span>
              </a>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-sm font-medium text-slate-900 mb-3">
            Status: <span className="text-brand-700 capitalize">{status}</span>
          </p>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3">{error}</p>}

          <div className="flex flex-col gap-2">
            {STATUS_ACTIONS.filter((a) => a.status !== status).map((a) => (
              <button
                key={a.status}
                onClick={() => updateStatus(a.status)}
                disabled={updating}
                className={`text-sm py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50 ${
                  a.status === 'dismissed'
                    ? 'text-slate-500 border border-slate-200 hover:bg-slate-50'
                    : 'bg-brand-950 text-white hover:bg-brand-900'
                }`}
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
