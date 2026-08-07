import { createContext, useContext, useEffect, useState } from 'react'
import { api, clearToken, setToken } from '../lib/api'

const AuthContext = createContext(undefined)

const USER_KEY = 'gradscout_user'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Optimistic: if a token and a cached profile already exist,
    // treat the user as signed in immediately rather than blocking
    // the first render on a network round trip. A token that's
    // actually expired or invalid gets caught the moment it's used
    // for a real request — see lib/api.js's 401 handling — not here.
    const cachedUser = localStorage.getItem(USER_KEY)
    if (cachedUser) {
      try {
        setUser(JSON.parse(cachedUser))
      } catch {
        clearToken()
        localStorage.removeItem(USER_KEY)
      }
    }
    setLoading(false)
  }, [])

  function persistSession(data) {
    setToken(data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setUser(data.user)
  }

  async function signUp(email, password) {
    const data = await api.post('/auth/signup', { email, password })
    persistSession(data)
  }

  async function signIn(email, password) {
    const data = await api.post('/auth/login', { email, password })
    persistSession(data)
  }

  function signOut() {
    clearToken()
    localStorage.removeItem(USER_KEY)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (ctx === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
