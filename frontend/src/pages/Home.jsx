import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { enablePushNotifications, getNotificationPermissionState } from '../lib/push'

export default function Home() {
  const [criteria, setCriteria] = useState(null) // null = still loading
  const [matchTotal, setMatchTotal] = useState(null)
  const [error, setError] = useState('')
  const [pushError, setPushError] = useState('')
  const [pushState, setPushState] = useState('unsupported') // 'unsupported' | 'default' | 'granted' | 'denied' | 'enabling'
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [deleting, setDeleting] = useState(false)
  const { signOut, deleteAccount, user } = useAuth()
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

  async function handleDeleteAccount() {
    setDeleteError('')
    setDeleting(true)
    try {
      await deleteAccount(deletePassword)
      navigate('/login')
    } catch (e) {
      setDeleteError(e.message)
      setDeleting(false)
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

        <div className="mt-8 pt-4 border-t border-slate-200">
          {!confirmingDelete ? (
            <div className="flex items-center justify-between">
              <Link to="/privacy" className="text-xs text-slate-400 underline hover:text-slate-600">
                Privacy Notice
              </Link>
              <button
                onClick={() => setConfirmingDelete(true)}
                className="text-xs text-slate-400 hover:text-red-600"
              >
                Delete my account
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <p className="text-sm font-medium text-slate-900">Delete your account?</p>
              <p className="text-xs text-slate-500 mt-1 mb-3">
                This permanently deletes your account, saved searches, and match history. There's
                no undo. Enter your password to confirm.
              </p>
              <input
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                placeholder="Your password"
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent mb-3"
              />
              {deleteError && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3">{deleteError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setConfirmingDelete(false)
                    setDeletePassword('')
                    setDeleteError('')
                  }}
                  className="flex-1 text-sm py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleting || !deletePassword}
                  className="flex-1 text-sm py-2 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {deleting ? 'Deleting…' : 'Delete permanently'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
