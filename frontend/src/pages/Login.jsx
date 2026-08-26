import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [searchParams] = useSearchParams()
  // Lets the marketing site's "Get started" CTAs link straight to
  // /app/login?mode=signup instead of landing everyone on Sign in and
  // making them find the toggle themselves.
  const [mode, setMode] = useState(searchParams.get('mode') === 'signup' ? 'signup' : 'signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { user, signIn, signUp } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    // Arriving here already signed in (bookmarked link, browser back
    // after login, etc.) should land back in the app, not ask them to
    // sign in again.
    if (user) navigate('/app', { replace: true })
  }, [user, navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (mode === 'signup') {
        await signUp(email, password)
      } else {
        await signIn(email, password)
      }
      navigate('/app')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="max-w-sm w-full">
        <div className="text-center mb-6">
          <Link to="/" className="inline-block">
            <h1 className="font-heading text-2xl font-bold text-primary-900">GradScout</h1>
          </Link>
          <p className="text-sm text-primary-600 mt-1">Graduate jobs, found for you.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm p-6 space-y-4">
          <div className="flex rounded-lg bg-secondary-100 p-1">
            <button
              type="button"
              onClick={() => setMode('signin')}
              className={`flex-1 text-sm font-medium py-1.5 rounded-md transition-colors ${
                mode === 'signin' ? 'bg-secondary-300 text-primary-900 shadow-sm' : 'text-primary-600'
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => setMode('signup')}
              className={`flex-1 text-sm font-medium py-1.5 rounded-md transition-colors ${
                mode === 'signup' ? 'bg-secondary-300 text-primary-900 shadow-sm' : 'text-primary-600'
              }`}
            >
              Sign up
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-700 mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-3.5 py-2.5 rounded-lg border border-primary-200 text-primary-900 placeholder:text-primary-400 focus:outline-none focus:ring-2 focus:ring-secondary-400 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-700 mb-1.5">Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              className="w-full px-3.5 py-2.5 rounded-lg border border-primary-200 text-primary-900 placeholder:text-primary-400 focus:outline-none focus:ring-2 focus:ring-secondary-400 focus:border-transparent"
            />
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-lg bg-accent-300 text-primary-900 text-sm font-semibold hover:bg-accent-400 transition-colors disabled:opacity-50"
          >
            {submitting ? 'Please wait…' : mode === 'signup' ? 'Create account' : 'Sign in'}
          </button>
        </form>

        {mode === 'signup' && (
          <p className="text-xs text-primary-400 text-center mt-4">
            No email confirmation needed — you'll be signed in right away.
          </p>
        )}

        <p className="text-xs text-primary-400 text-center mt-3">
          By continuing, you agree to the{' '}
          <Link to="/terms" className="underline hover:text-primary-600">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="underline hover:text-primary-600">
            Privacy Notice
          </Link>
          .
        </p>

        <p className="text-xs text-primary-400 text-center mt-6">
          <Link to="/" className="hover:text-primary-600">
            ← Back to gradscout.uk
          </Link>
        </p>
      </div>
    </div>
  )
}
