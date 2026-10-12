// Wraps backend/app/routes/actions.py and savings.py (URLs /api/actions and /api/savings)
import { post, request } from './httpClient.js'

export function switchOffAppliance({ room_id, equipment_id, notes = '' }) {
  return post('/actions/switch-off', { room_id, equipment_id, notes })
}

export function getActions({ limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({ limit, offset })
  return request(`/actions?${params.toString()}`)
}

export function getAction(actionId) {
  return request(`/actions/${actionId}`)
}

export function getSavingsRecords({ limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({ limit, offset })
  return request(`/savings/records?${params.toString()}`)
}

export function getSavingsSummary({ from, to } = {}) {
  const params = new URLSearchParams()
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  return request(`/savings/summary?${params.toString()}`)
}
