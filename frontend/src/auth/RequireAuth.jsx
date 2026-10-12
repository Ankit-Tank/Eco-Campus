import { Navigate } from 'react-router-dom'
import { getToken, getUser } from './session.js'

// Wrap a page with this to protect it. Optional: roles={['admin']} to limit it to admins.
// This only improves the experience. The real permission check happens in the backend
// (backend/app/core/deps.py) on every request.
export default function RequireAuth({ children, roles }) {
  const user = getUser()

  if (!getToken() || !user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />

  return children
}
