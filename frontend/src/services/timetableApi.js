// Wraps backend/app/routes/timetable.py (URL /api/timetable)
import { post, request } from './httpClient.js'

export function getTimetable({ room_id, day_of_week } = {}) {
  const params = new URLSearchParams()
  if (room_id) params.append('room_id', room_id)
  if (day_of_week !== undefined && day_of_week !== null && day_of_week !== '') params.append('day_of_week', day_of_week)
  return request(`/timetable?${params.toString()}`)
}

// ---- admin only (the backend enforces the role) ----
export function createTimetableEntry({ room_id, day_of_week, start_time, end_time, activity, expected_students }) {
  return post('/timetable', {
    room_id: Number(room_id),
    day_of_week: Number(day_of_week),
    start_time,
    end_time,
    activity,
    expected_students: Number(expected_students),
  })
}

export function updateTimetableEntry(id, fields) {
  return request(`/timetable/${id}`, { method: 'PUT', body: JSON.stringify(fields) })
}

export function deleteTimetableEntry(id) {
  return request(`/timetable/${id}`, { method: 'DELETE' })
}
