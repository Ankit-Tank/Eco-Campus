// Wraps backend/app/routes/timetable.py (URL /api/timetable)
import { request } from './httpClient.js'

export function getTimetable({ room_id, day_of_week } = {}) {
  const params = new URLSearchParams()
  if (room_id) params.append('room_id', room_id)
  if (day_of_week) params.append('day_of_week', day_of_week)
  return request(`/timetable?${params.toString()}`)
}
