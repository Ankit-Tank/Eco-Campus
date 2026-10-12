// Wraps backend/app/routes/ghost_load.py (URL /api/ghost)
import { request } from './httpClient.js'

export function getGhostCurrent() {
  return request('/ghost/current')
}

export function getGhostRanking({ period = 'week', date_from, date_to, limit = 12, offset = 0 } = {}) {
  const params = new URLSearchParams({ period })
  if (date_from) params.append('from', date_from)
  if (date_to) params.append('to', date_to)
  if (limit) params.append('limit', limit)
  if (offset) params.append('offset', offset)
  return request(`/ghost/ranking?${params.toString()}`)
}

export function getSwitchOffList() {
  return request('/ghost/switch-off-list')
}

export function explainRoomGhost(roomId) {
  return request(`/ghost/room/${roomId}/explain`)
}
