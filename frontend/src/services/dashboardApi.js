// Wraps backend/app/routes/dashboard.py
import { request } from './httpClient.js'
import { USE_MOCK } from '../config.js'
import { MOCK_PUBLIC_IMPACT } from './mock/mockDashboard.js'
import * as mockAdmin from './mock/mockAdmin.js'
import * as mockStudent from './mock/mockStudent.js'

// GET /api/dashboard/public-impact   (no login needed, used by the login page)
//   -> { is_simulated, cards: [{ key, value, unit, change_pct, equivalent_value }] }
export async function getPublicImpact() {
  if (USE_MOCK) return MOCK_PUBLIC_IMPACT
  return request('/dashboard/public-impact')
}

// GET /api/dashboard/admin-overview?from=YYYY-MM-DD&to=YYYY-MM-DD&zone=all   (admin only)
//   -> { is_simulated, zones: [{ key, name }],
//        kpis: { conserved_mwh, consumption_mwh, consumption_change_pct, co2_saved_tonnes },
//        series: [{ date, actual_kw, baseline_kw }], optimization_events: [{ date }],
//        blocks: [{ key, name, share_pct, kwh }], total_kwh,
//        buildings: [{ name, active_kw, daily_var_pct, status: 'exceeded' | 'normal' | 'below' }] }
export async function getAdminOverview({ from, to, zone = 'all' }) {
  if (USE_MOCK) return mockAdmin.getAdminOverview({ from, to, zone })
  return request('/dashboard/admin-overview?' + new URLSearchParams({ from, to, zone }))
}

// GET /api/dashboard/student-home   (the logged-in student's own numbers only)
//   -> { is_simulated, name,
//        stats: { reports_filed, accepted, in_progress, estimated_saving_kwh },
//        recent: [complaint], impact: { electricity_kwh, water_litres, co2_kg } }
export async function getStudentHome(user) {
  if (USE_MOCK) return mockStudent.getStudentHome(user)
  return request('/dashboard/student-home')
}

// GET /api/dashboard/summary (all users)
export async function getDashboardSummary({ from, to } = {}) {
  const params = new URLSearchParams()
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  return request(`/dashboard/summary?${params.toString()}`)
}

