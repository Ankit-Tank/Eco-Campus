// Wraps backend/app/routes/dashboard.py
import { request } from './httpClient.js'
import { USE_MOCK } from '../config.js'
import { MOCK_PUBLIC_IMPACT } from './mock/mockDashboard.js'

// GET /api/dashboard/public-impact   (no login needed, used by the login page)
//   -> { is_simulated, cards: [{ key, value, unit, change_pct, equivalent_value }] }
export async function getPublicImpact() {
  if (USE_MOCK) return MOCK_PUBLIC_IMPACT
  return request('/dashboard/public-impact')
}

// Add the logged-in dashboard calls here later, for example:
// export const getOverview = (params) => request('/dashboard/overview?' + new URLSearchParams(params))
