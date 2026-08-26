import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import BottomNav from '../components/BottomNav'

export default function Home() {
  const [criteria, setCriteria] = useState(null) // null = still loading
  const [matchTotal, setMatchTotal] = useState(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api
      .get('/criteria')
      .then(setCriteria)
      .catch((e) => setError(e.message))
    // Deliberately no auto-redirect to /criteria here for a first-time
    // user with zero saved searches - that used to skip this screen
    // entirely, which meant nobody ever actually landed on the app's
    // home/hub screen on their very first visit. Now everyone lands
    // here first; a brand-new user just sees the empty state below
    // instead of the normal two tiles, with its own clear way in to
    // creating their first search.
  }, [])

  useEffect(() => {
    if (criteria && criteria.length > 0) {
      // limit=1 just to read `total` cheaply for a live count, without
      // pulling down every match just to show a badge on this screen.
      api.get('/feed?limit=1').then((data) => setMatchTotal(data.total)).catch(() => setMatchTotal(null))
    }
  }, [criteria])

  const isFirstVisit = criteria !== null && criteria.length === 0

  return (
    <div className="min-h-screen bg-background px-4 py-8 pb-24">
      <div className="max-w-sm mx-auto">
        <div className="mb-8">
          <h1 className="font-heading text-2xl font-bold text-primary-900">GradScout</h1>
          <p className="text-sm text-primary-600 mt-1">Graduate jobs, found for you.</p>
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-4">{error}</p>}

        {isFirstVisit ? (
          <div className="bg-secondary-100 border border-secondary-200 rounded-2xl p-5">
            <p className="font-heading text-base font-bold text-primary-900">Let's find you some jobs</p>
            <p className="text-sm text-primary-700 mt-1.5 leading-relaxed">
              Create a search with the keywords, locations, and industries you care about, and
              we'll start matching graduate jobs against it automatically.
            </p>
            <button
              onClick={() => navigate('/app/criteria')}
              className="w-full mt-4 py-2.5 rounded-lg bg-accent-300 text-primary-900 text-sm font-semibold hover:bg-accent-400 transition-colors"
            >
              Create your first search
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <button
              onClick={() => navigate('/app/feed')}
              className="w-full bg-secondary-100 border border-secondary-200 rounded-2xl p-5 text-left hover:bg-secondary-200 transition-colors"
            >
              <p className="font-heading text-sm font-bold text-primary-900">Your matches</p>
              <p className="text-xs text-primary-700 mt-1">
                {matchTotal === null ? 'View your job feed' : `${matchTotal} job${matchTotal === 1 ? '' : 's'} matching your searches`}
              </p>
            </button>

            <button
              onClick={() => navigate('/app/criteria')}
              className="w-full bg-white rounded-2xl shadow-sm p-5 text-left hover:shadow-md transition-shadow border border-primary-100"
            >
              <p className="font-heading text-sm font-bold text-primary-900">Your search criteria</p>
              <p className="text-xs text-primary-500 mt-1">
                {criteria === null ? 'Loading…' : `${criteria.length} saved search${criteria.length === 1 ? '' : 'es'}`}
              </p>
            </button>
          </div>
        )}
      </div>
      <BottomNav />
    </div>
  )
}
