import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import InstallBanner from './components/InstallBanner'
import Landing from './pages/marketing/Landing'
import NotFound from './pages/marketing/NotFound'
import Login from './pages/Login'
import Home from './pages/Home'
import Criteria from './pages/Criteria'
import JobFeed from './pages/JobFeed'
import JobDetail from './pages/JobDetail'
import Settings from './pages/Settings'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public site — gradscout.uk's marketing pages. Legal pages
              live at the top level (not under /app) since they're
              linked from both the site footer and from inside the app,
              and /privacy is what's worth sharing or having indexed —
              not /app/privacy. */}
          <Route path="/" element={<Landing />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />

          {/* The product — everything that requires (or leads to)
              signing in lives under /app, so one domain can serve both
              the marketing site and GradScout itself without the two
              fighting over the same routes. */}
          <Route path="/app/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/app" element={<Home />} />
            <Route path="/app/criteria" element={<Criteria />} />
            <Route path="/app/feed" element={<JobFeed />} />
            <Route path="/app/jobs/:matchId" element={<JobDetail />} />
            <Route path="/app/settings" element={<Settings />} />
          </Route>
          <Route path="/app/*" element={<Navigate to="/app" replace />} />

          <Route path="*" element={<NotFound />} />
        </Routes>
        <InstallBanner />
      </BrowserRouter>
    </AuthProvider>
  )
}
