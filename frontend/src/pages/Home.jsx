import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { enablePushNotifications, getNotificationPermissionState } from '../lib/push'

export default function Home() {
  const [criteria, setCriteria] = useState(null) // null = still loading
  const [matchTotal, setMatchTotal] = useState(null)
  const [error, setError] = useState('')
  const [pushError, setPushError] = useState('')
  const [pushState, setPushState] = useState('unsupported') // 'unsupported' | 'default' | 'granted' | 'denied' | 'enabling'
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

  useEffect(() => {
    setPushState(getNotificationPermissionState())
  }, [])

  function handleSignOut() {
    signOut()
    navigate('/login')
  }

  async function handleEnablePush() {
    setPushError('')
    setPushState('enabling')
    try {
      await enablePushNotifications()
      setPushState('granted')
    } catch (e) {
      setPushError(e.message)
      setPushState(getNotificationPermissionState())
    }
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

        {pushState !== 'unsupported' && (
          <div className="w-full bg-white rounded-2xl shadow-sm p-5 mt-3">
            <p className="text-sm font-medium text-slate-900">Notifications</p>

            {pushState === 'granted' ? (
              <p className="text-xs text-slate-500 mt-1">
                You'll be notified the moment a new job matches your search.
              </p>
            ) : pushState === 'denied' ? (
              <p className="text-xs text-slate-500 mt-1">
                Notifications are blocked for this app — enable them in your browser or phone's
                settings to turn this on.
              </p>
            ) : (
              <>
                <p className="text-xs text-slate-500 mt-1 mb-3">
                  Get notified the moment a new job matches your search, even when the app isn't open.
                </p>
                <button
                  onClick={handleEnablePush}
                  disabled={pushState === 'enabling'}
                  className="text-sm px-4 py-2 rounded-lg bg-brand-950 text-white font-medium hover:bg-brand-900 transition-colors disabled:opacity-50"
                >
                  {pushState === 'enabling' ? 'Enabling…' : 'Enable notifications'}
                </button>
              </>
            )}

            {pushError && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-3">{pushError}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
