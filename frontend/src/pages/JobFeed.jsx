import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star, X } from 'lucide-react'
import { api } from '../lib/api'
import { timeAgo } from '../lib/time'
import BackButton from '../components/BackButton'
import BottomNav from '../components/BottomNav'

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

/** Does this match still belong under the currently active tab, after a local optimistic update? */
function matchesFilter(match, filter) {
  if (filter.favouritesOnly && !match.is_favourite) return false
  if (filter.status && match.status !== filter.status) return false
  return true
}

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
    setItems((prev) =>
      prev
        .map((m) => (m.id === matchId ? { ...m, is_favourite: nextValue } : m))
        .filter((m) => m.id !== matchId || matchesFilter(m, activeFilter)),
    )
    api.patch(`/matches/${matchId}`, { is_favourite: nextValue }).catch(() => {
      setError('Could not update that — please try again.')
      load(0, true) // local list may have dropped the item optimistically; simplest correct recovery is a fresh load
    })
  }

  function handleDismiss(matchId) {
    const previous = items
    setItems((prev) =>
      prev
        .map((m) => (m.id === matchId ? { ...m, status: 'dismissed' } : m))
        .filter((m) => m.id !== matchId || matchesFilter(m, activeFilter)),
    )
    api.patch(`/matches/${matchId}`, { status: 'dismissed' }).catch(() => {
      setItems(previous)
      setError('Could not update that — please try again.')
    })
  }

  const hasMore = offset + PAGE_SIZE < total

  return (
    <div className="min-h-screen bg-background px-4 py-8 pb-24">
      <div className="max-w-sm mx-auto">
        <div className="mb-2">
          <BackButton onClick={() => navigate('/app')} />
        </div>

        <h1 className="font-heading text-lg font-bold text-primary-900 mb-1">Your matches</h1>
        <p className="text-sm text-primary-600 mb-1">Jobs matching your saved searches, newest first.</p>
        <p className="text-xs text-primary-400 mb-4">Tip: swipe a card left to favourite, right to dismiss.</p>

        <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setActiveFilter(f)}
              className={`text-sm px-3 py-1.5 rounded-full border whitespace-nowrap transition-colors ${
                activeFilter.key === f.key
                  ? 'bg-secondary-300 border-secondary-300 text-primary-900 font-medium'
                  : 'bg-white border-primary-200 text-primary-600'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-4">{error}</p>}

        {loading ? (
          <p className="text-sm text-primary-400">Loading…</p>
        ) : items.length === 0 ? (
          <div className="bg-white rounded-2xl shadow-sm p-6 text-center">
            <p className="text-sm text-primary-500">
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
              <SwipeableJobCard
                key={match.id}
                match={match}
                onOpen={() => navigate(`/app/jobs/${match.id}`)}
                onToggleFavourite={(next) => handleToggleFavourite(match.id, next)}
                onDismiss={() => handleDismiss(match.id)}
              />
            ))}
          </div>
        )}

        {hasMore && !loading && (
          <button
            onClick={() => load(offset + PAGE_SIZE, false)}
            disabled={loadingMore}
            className="w-full mt-4 py-2.5 rounded-lg border border-primary-200 text-sm font-medium text-primary-600 bg-white hover:bg-secondary-50 transition-colors disabled:opacity-50"
          >
            {loadingMore ? 'Loading…' : 'Load more'}
          </button>
        )}
      </div>
      <BottomNav />
    </div>
  )
}

// Distance (px) a card must be dragged past before releasing commits
// the swipe action, rather than snapping back to centre.
const SWIPE_COMMIT_THRESHOLD = 88
// How far a committed card flies offscreen before it's removed from
// the list — matched to the CSS transition duration below.
const FLY_OUT_DISTANCE = 400
const FLY_OUT_MS = 220

function SwipeableJobCard({ match, onOpen, onToggleFavourite, onDismiss }) {
  const [dragX, setDragX] = useState(0)
  const [phase, setPhase] = useState('idle') // 'idle' | 'dragging' | 'flying-left' | 'flying-right'
  const pointerState = useRef(null) // { id, startX, startY, isHorizontal }

  function handlePointerDown(e) {
    if (phase !== 'idle') return
    pointerState.current = { id: e.pointerId, startX: e.clientX, startY: e.clientY, isHorizontal: false }
  }

  function handlePointerMove(e) {
    const state = pointerState.current
    if (!state || state.id !== e.pointerId || phase === 'flying-left' || phase === 'flying-right') return

    const dx = e.clientX - state.startX
    const dy = e.clientY - state.startY

    if (!state.isHorizontal) {
      // Decide once, early, whether this gesture is a horizontal swipe
      // or a vertical scroll - and only commit to intercepting it (via
      // setPointerCapture) once it's clearly horizontal, so a normal
      // vertical scroll through the list is never hijacked mid-drag.
      if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return
      if (Math.abs(dy) > Math.abs(dx)) {
        pointerState.current = null // vertical scroll - let the browser handle it, stop tracking this gesture
        return
      }
      state.isHorizontal = true
      setPhase('dragging')
      e.currentTarget.setPointerCapture(e.pointerId)
    }

    setDragX(dx)
  }

  function handlePointerUp(e) {
    const state = pointerState.current
    if (!state || state.id !== e.pointerId) return
    pointerState.current = null

    if (!state.isHorizontal) return // was a tap, or a vertical scroll already handed off - onClick handles the tap case

    if (dragX <= -SWIPE_COMMIT_THRESHOLD) {
      setPhase('flying-left')
      setDragX(-FLY_OUT_DISTANCE)
      setTimeout(() => {
        onToggleFavourite(true)
        // If the parent's list still contains this card after the
        // update (e.g. it's still favourited AND still matches the
        // active tab), this component stays mounted rather than being
        // removed - reset it, or it would stay flown offscreen forever
        // instead of settling back into the list in its new state.
        setPhase('idle')
        setDragX(0)
      }, FLY_OUT_MS)
    } else if (dragX >= SWIPE_COMMIT_THRESHOLD) {
      setPhase('flying-right')
      setDragX(FLY_OUT_DISTANCE)
      setTimeout(() => {
        onDismiss()
        setPhase('idle')
        setDragX(0)
      }, FLY_OUT_MS)
    } else {
      setPhase('idle')
      setDragX(0)
    }
  }

  function handleClick() {
    // A real drag (even one that snapped back) shouldn't also open the
    // job - only a genuine tap, with no meaningful pointer movement, does.
    if (pointerState.current?.isHorizontal) return
    onOpen()
  }

  const favouriteReveal = Math.max(0, Math.min(1, -dragX / SWIPE_COMMIT_THRESHOLD))
  const dismissReveal = Math.max(0, Math.min(1, dragX / SWIPE_COMMIT_THRESHOLD))
  const isDragging = phase === 'dragging'

  return (
    <div className="relative">
      {/* Swipe-action track, revealed from behind the card as it moves. */}
      <div className="absolute inset-0 rounded-2xl overflow-hidden flex" aria-hidden="true">
        <div
          className="flex items-center gap-2 px-5 bg-primary-800 text-background transition-opacity"
          style={{ opacity: dismissReveal, width: '50%' }}
        >
          <X size={20} />
          <span className="text-sm font-medium">Dismiss</span>
        </div>
        <div
          className="flex items-center justify-end gap-2 px-5 bg-accent-300 text-primary-900 ml-auto transition-opacity"
          style={{ opacity: favouriteReveal, width: '50%' }}
        >
          <span className="text-sm font-medium">Favourite</span>
          <Star size={20} fill="currentColor" />
        </div>
      </div>

      <div
        role="button"
        tabIndex={0}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onClick={handleClick}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onOpen()}
        style={{
          transform: `translateX(${dragX}px)`,
          transition: isDragging ? 'none' : `transform ${FLY_OUT_MS}ms ease-out`,
          touchAction: 'pan-y',
        }}
        className="relative"
      >
        <JobCard match={match} onToggleFavourite={onToggleFavourite} />
      </div>
    </div>
  )
}

function JobCard({ match, onToggleFavourite }) {
  const { job, status, is_favourite: isFavourite } = match
  const isDismissed = status === 'dismissed'
  const isExpired = job.is_expired
  const meta = [
    job.location_category || job.location,
    job.salary_text,
    job.contract_type,
    timeAgo(job.posted_date || job.first_seen_at),
  ].filter(Boolean)

  return (
    <div
      className={`w-full bg-white rounded-2xl shadow-sm p-4 text-left cursor-pointer select-none ${
        isDismissed || isExpired ? 'opacity-50' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className={`font-heading text-sm font-bold text-primary-900 truncate ${isDismissed ? 'line-through' : ''}`}>
            {job.title}
          </p>
          <p className="text-xs text-primary-500 mt-0.5">{job.company}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {isExpired && (
            <span className="text-[10px] uppercase tracking-wide font-medium text-primary-500 bg-primary-100 px-2 py-0.5 rounded-full">
              Expired
            </span>
          )}
          {status !== 'new' && (
            <span className="text-[10px] uppercase tracking-wide font-medium text-primary-700 bg-secondary-100 px-2 py-0.5 rounded-full">
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
            className="p-1 -m-1 text-primary-300 hover:text-accent-400 transition-colors"
          >
            <Star size={18} fill={isFavourite ? 'currentColor' : 'none'} className={isFavourite ? 'text-accent-300' : ''} />
          </button>
        </div>
      </div>

      {meta.length > 0 && <p className="text-xs text-primary-400 mt-2">{meta.join(' · ')}</p>}

      {job.industry_category && (
        <span className="inline-block mt-2 text-[11px] text-primary-600 bg-primary-50 px-2 py-0.5 rounded-md">
          {job.industry_category}
        </span>
      )}

      {job.sources.length > 1 && (
        <p className="text-[11px] text-primary-400 mt-2">
          Also found on {job.sources.length - 1} other site{job.sources.length > 2 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
