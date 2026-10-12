import { Navigate } from 'react-router-dom'
import { getUser } from '../auth/session.js'

// The login pages send everyone to /dashboard. This sends each role to its own home.
export default function Dashboard() {
  const user = getUser()
  return <Navigate to={user?.role === 'admin' ? '/admin/overview' : '/student/home'} replace />
}
