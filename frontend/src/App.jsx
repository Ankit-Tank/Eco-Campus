import { Navigate, Route, Routes } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import RequireAuth from './auth/RequireAuth.jsx'
import AppShell from './layouts/AppShell.jsx'
import AdminOverview from './pages/admin/AdminOverview.jsx'
import AdminElectricity from './pages/admin/AdminElectricity.jsx'
import AdminWater from './pages/admin/AdminWater.jsx'
import AdminAlerts from './pages/admin/AdminAlerts.jsx'
import AdminMaintenance from './pages/admin/AdminMaintenance.jsx'
import AdminReports from './pages/admin/AdminReports.jsx'
import AdminSimulator from './pages/admin/AdminSimulator.jsx'
import AdminSettings from './pages/admin/AdminSettings.jsx'
import LeaderboardView from './pages/LeaderboardView.jsx'
import StudentHome from './pages/student/StudentHome.jsx'
import StudentChat from './pages/student/StudentChat.jsx'
import StudentMyReports from './pages/student/StudentMyReports.jsx'
import StudentImpact from './pages/student/StudentImpact.jsx'
import StudentCampus from './pages/student/StudentCampus.jsx'
import AdminRooms from './pages/admin/AdminRooms.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Login sends everyone here; it forwards each role to its own home page. */}
      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />

      {/* Admin area. RequireAuth is only for the experience; the backend checks the role on every request. */}
      <Route
        path="/admin"
        element={
          <RequireAuth roles={['admin']}>
            <AppShell variant="admin" />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="overview" replace />} />
        <Route path="overview" element={<AdminOverview />} />
        <Route path="electricity" element={<AdminElectricity />} />
        <Route path="water" element={<AdminWater />} />
        <Route path="alerts" element={<AdminAlerts />} />
        <Route path="maintenance" element={<AdminMaintenance />} />
        <Route path="rooms" element={<AdminRooms />} />
        <Route path="leaderboard" element={<LeaderboardView />} />
        <Route path="reports" element={<AdminReports />} />
        <Route path="simulator" element={<AdminSimulator />} />
        <Route path="settings" element={<AdminSettings />} />
      </Route>

      {/* Student area */}
      <Route
        path="/student"
        element={
          <RequireAuth roles={['student']}>
            <AppShell variant="student" />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="home" replace />} />
        <Route path="home" element={<StudentHome />} />
        <Route path="chat" element={<StudentChat />} />
        <Route path="my-reports" element={<StudentMyReports />} />
        <Route path="campus" element={<StudentCampus />} />
        <Route path="impact" element={<StudentImpact />} />
        <Route path="leaderboard" element={<LeaderboardView />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
