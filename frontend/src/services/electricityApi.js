// Wraps backend/app/routes/electricity.py (URL /api/electricity)
import { request } from './httpClient.js'

export function getElectricitySeries({ block, room, from, to, limit = 200, offset = 0 } = {}) {
  const params = new URLSearchParams()
  if (block && block !== 'all') params.append('block', block)
  if (room && room !== 'all') params.append('room', room)
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  if (limit) params.append('limit', limit)
  if (offset) params.append('offset', offset)
  return request(`/electricity/series?${params.toString()}`)
}
