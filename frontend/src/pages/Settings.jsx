import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { enablePushNotifications, getNotificationPermissionState } from '../lib/push'
import BottomNav from '../components/BottomNav'

export default function Settings() {
  const [pushError, setPushError] = useState('')
  const [pushState, setPushState] = useState('unsupported') // 'unsupported' | 'default' | 'granted' | 'denied' | 'enabling'
  const [digestSaving, setDigestSaving] = useState(false)
  const [digestError, setDigestError] = useState('')
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [deleting, setDeleting] = useState(false)
  const { signOut, deleteAccount, updateSettings, user } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    setPushState(getNotificationPermissionState())
  }, [])

  function handleSignOut() {
    signOut()
    navigate('/app/login')
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

  async function handleToggleDigest(nextValue) {
    setDigestError('')
    setDigestSaving(true)
    try {
      await updateSettings({ email_digest_enabled: nextValue })
    } catch (e) {
      setDigestError(e.message)
    } finally {
      setDigestSaving(false)
    }
  }

  async function handleDeleteAccount() {
    setDeleteError('')
    setDeleting(true)
    try {
      await deleteAccount(deletePassword)
      navigate('/app/login')
    } catch (e) {
      setDeleteError(e.message)
      setDeleting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background px-4 py-8 pb-24">
      <div className="max-w-sm mx-auto">
        <h1 className="font-heading text-2xl font-bold text-primary-900 mb-1">Settings</h1>
        {user?.email && <p className="text-sm text-primary-500 mb-8">{user.email}</p>}

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-3 border border-primary-100">
          <div className="flex items-center justify-between">
            <p className="font-heading text-sm font-bold text-primary-900">Account</p>
            <button
              onClick={handleSignOut}
              className="text-sm font-medium text-primary-600 hover:text-primary-900 border border-primary-200 rounded-lg px-3 py-1.5 hover:bg-primary-50 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>

        {pushState !== 'unsupported' && (
          <div className="bg-white rounded-2xl shadow-sm p-5 mb-3 border border-primary-100">
            <p className="font-heading text-sm font-bold text-primary-900">Push notifications</p>

            {pushState === 'granted' ? (
              <p className="text-xs text-primary-500 mt-1">
                You'll be notified the moment a new job matches your search.
              </p>
            ) : pushState === 'denied' ? (
              <p className="text-xs text-primary-500 mt-1">
                Notifications are blocked for this app — enable them in your browser or phone's
                settings to turn this on.
              </p>
            ) : (
              <>
                <p className="text-xs text-primary-500 mt-1 mb-3">
                  Get notified the moment a new job matches your search, even when the app isn't open.
                </p>
                <button
                  onClick={handleEnablePush}
                  disabled={pushState === 'enabling'}
                  className="text-sm px-4 py-2 rounded-lg bg-accent-300 text-primary-900 font-semibold hover:bg-accent-400 transition-colors disabled:opacity-50"
                >
                  {pushState === 'enabling' ? 'Enabling…' : 'Enable notifications'}
                </button>
              </>
            )}

            {pushError && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-3">{pushError}</p>}
          </div>
        )}

        {/* Not gated behind push support — this is precisely the
            channel for people WITHOUT it (iOS Safari without the PWA
            installed, browsers where push is unavailable, etc.), so it
            needs to always be visible, not conditional on the section
            above. */}
        <div className="bg-white rounded-2xl shadow-sm p-5 mb-3 border border-primary-100">
          <div className="flex items-center justify-between">
            <div className="pr-3">
              <p className="font-heading text-sm font-bold text-primary-900">Email digest</p>
              <p className="text-xs text-primary-500 mt-0.5">
                A weekly summary of new matches, sent to your email.
              </p>
            </div>
            <Toggle
              checked={user?.email_digest_enabled ?? true}
              onChange={handleToggleDigest}
              disabled={digestSaving}
            />
          </div>
          {digestError && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mt-3">{digestError}</p>}
        </div>

        <div className="bg-white rounded-2xl shadow-sm p-5 mb-3 border border-primary-100 space-y-2">
          <Link to="/terms" className="block text-sm font-medium text-primary-700 hover:text-primary-900">
            Terms of Service
          </Link>
          <Link to="/privacy" className="block text-sm font-medium text-primary-700 hover:text-primary-900">
            Privacy Notice
          </Link>
        </div>

        <div className="mt-6 pt-4 border-t border-primary-200">
          {!confirmingDelete ? (
            <button
              onClick={() => setConfirmingDelete(true)}
              className="text-xs text-primary-400 hover:text-red-600"
            >
              Delete my account
            </button>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm p-5 border border-red-100">
              <p className="font-heading text-sm font-bold text-primary-900">Delete your account?</p>
              <p className="text-xs text-primary-500 mt-1 mb-3">
                This permanently deletes your account, saved searches, and match history. There's
                no undo. Enter your password to confirm.
              </p>
              <input
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                placeholder="Your password"
                className="w-full px-3.5 py-2.5 rounded-lg border border-primary-200 text-sm text-primary-900 placeholder:text-primary-400 focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent mb-3"
              />
              {deleteError && <p className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3">{deleteError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setConfirmingDelete(false)
                    setDeletePassword('')
                    setDeleteError('')
                  }}
                  className="flex-1 text-sm py-2 rounded-lg border border-primary-200 text-primary-600 hover:bg-primary-50 transition-colors"
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
      <BottomNav />
    </div>
  )
}

/**
 * A real iOS-style toggle switch — the design brief specifically calls
 * out toggle switches as one of the few places the accent colour
 * (#E0A96D) should be used, so this is the one genuinely literal
 * "toggle switch" in the app rather than a button styled to look
 * switch-like.
 */
function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
        checked ? 'bg-accent-300' : 'bg-primary-200'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}
