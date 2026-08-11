import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'

export default function Home() {
  const [criteria, setCriteria] = useState(null) // null = still loading
  const [matchTotal, setMatchTotal] = useState(null)
  const [error, setError] = useState('')
  const { signOut, user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    api
      .get('/criteria')
      .then((data) => {
        setCriteria(data)
        if (data.length === 0) {
          // Onboarding: a brand-new user with no saved search yet has
          // nothing useful to do on this hub screen, so skip it
          // entirely and go straight to setting one up. Returning
          // users who already have criteria land here normally.
          navigate('/criteria', { replace: true })
        }
      })
      .catch((e) => setError(e.message))
  }, [navigate])

  useEffect(() => {
    if (criteria && criteria.length > 0) {
      // limit=1 just to read `total` cheaply for a live count, without
      // pulling down every match just to show a badge on this screen.
      api.get('/feed?limit=1').then((data) => setMatchTotal(data.total)).catch(() => setMatchTotal(null))
    }
  }, [criteria])

  function handleSignOut() {
    signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8">
      <div className="max-w-sm mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">GradScout</h1>
            {user?.email && <p className="text-xs text-slate-400 mt-0.5">{user.email}</p>}
          </div>
          <button onClick={handleSignOut} className="text-sm text-slate-500 hover:text-slate-700">
            Sign out
          </button>
        </div>

        <button
          onClick={() => navigate('/feed')}
          className="w-full bg-white rounded-2xl shadow-sm p-5 text-left hover:shadow-md transition-shadow mb-3"
        >
          <p className="text-sm font-medium text-slate-900">Your matches</p>
          <p className="text-xs text-slate-500 mt-1">
            {matchTotal === null ? 'View your job feed' : `${matchTotal} job${matchTotal === 1 ? '' : 's'} matching your searches`}
          </p>
        </button>

        <button
          onClick={() => navigate('/criteria')}
          className="w-full bg-white rounded-2xl shadow-sm p-5 text-left hover:shadow-md transition-shadow"
        >
          <p className="text-sm font-medium text-slate-900">Your search criteria</p>
          <p className="text-xs text-slate-500 mt-1">
            {error
              ? 'Could not load your searches'
              : criteria === null
                ? 'Loading…'
                : `${criteria.length} saved search${criteria.length === 1 ? '' : 'es'}`}
          </p>
        </button>
      </div>
    </div>
  )
}
