/**
 * Thin fetch wrapper for the FastAPI backend. Attaches the current
 * access token (see context/AuthContext.jsx) as a standard
 * `Authorization: Bearer <token>` header on every request.
 *
 * No Supabase client here — GradScout issues and verifies its own
 * tokens now (see the backend's app/security.py), so this is just a
 * plain localStorage-backed token, not a session object with its own
 * refresh machinery to manage.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL
const TOKEN_KEY = 'gradscout_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request(method, path, body) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    // Missing, expired, or points at a deleted account — none of
    // these are recoverable without signing in again, so clear
    // whatever's stored and force back to the login screen rather
    // than leaving the app sitting in a broken half-authenticated
    // state.
    clearToken()
    localStorage.removeItem('gradscout_user')
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login'
    }
    throw new Error('Session expired — please sign in again')
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const errBody = await res.json()
      detail = errBody.detail || detail
    } catch {
      // Response wasn't JSON — fall back to statusText.
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  patch: (path, body) => request('PATCH', path, body),
  delete: (path, body) => request('DELETE', path, body),
}
