import { Navigate, Route, Routes } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import RequireAuth from './auth/RequireAuth.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />

      {/* Example of an admin-only page for later:
      <Route path="/settings" element={<RequireAuth roles={['admin']}><Settings /></RequireAuth>} />
      */}

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
