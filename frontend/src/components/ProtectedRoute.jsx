import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-sm text-primary-400">Loading…</p>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/app/login" replace />
  }

  return <Outlet />
}
