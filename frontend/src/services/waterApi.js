// Wraps backend/app/routes/water.py (URL /api/water)
import { request } from './httpClient.js'

export function getWaterSeries({ location_id, from, to } = {}) {
  const params = new URLSearchParams()
  if (location_id && location_id !== 'all') params.append('location_id', location_id)
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  return request(`/water/series?${params.toString()}`)
}

export function getWaterLocations() {
  return request('/water/locations')
}

export function getWaterAlerts() {
  return request('/water/alerts')
}

export function patchWaterAlert(alertId, { status, inspection_notes }) {
  return request(`/water/alerts/${alertId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status, inspection_notes }),
  })
}
