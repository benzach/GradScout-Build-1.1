import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import InstallBanner from './components/InstallBanner'
import Login from './pages/Login'
import Home from './pages/Home'
import Criteria from './pages/Criteria'
import JobFeed from './pages/JobFeed'
import JobDetail from './pages/JobDetail'
import Privacy from './pages/Privacy'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Home />} />
            <Route path="/criteria" element={<Criteria />} />
            <Route path="/feed" element={<JobFeed />} />
            <Route path="/jobs/:matchId" element={<JobDetail />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <InstallBanner />
      </BrowserRouter>
    </AuthProvider>
  )
}
