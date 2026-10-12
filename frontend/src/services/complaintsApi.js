// Wraps backend/app/routes/complaints.py and student appliance-left-on report
import { post, request } from './httpClient.js'
import { USE_MOCK } from '../config.js'
import * as mock from './mock/mockStudent.js'

// GET /api/complaints/mine (students only)
export function getMyComplaints() {
  if (USE_MOCK) return mock.getMyComplaints()
  return request('/complaints/mine')
}

// GET /api/complaints (all complaints with filters for admin)
export function getComplaints({ status, building, category, limit = 100, offset = 0 } = {}) {
  const params = new URLSearchParams()
  if (status && status !== 'all') params.append('status', status)
  if (building && building !== 'all') params.append('building', building)
  if (category && category !== 'all') params.append('category', category)
  params.append('limit', limit)
  params.append('offset', offset)
  return request(`/complaints?${params.toString()}`)
}

// GET /api/complaints/:id
export function getComplaint(id) {
  return request(`/complaints/${id}`)
}

// POST /api/complaints (multipart form data)
export function createComplaint({ title, category, location, description, image }) {
  const form = new FormData()
  if (title) form.append('title', title)
  if (category) form.append('category', category)
  if (location) form.append('location', location)
  if (description) form.append('description', description)
  if (image) form.append('photo', image)
  if (USE_MOCK) return mock.createComplaint(form)
  return request('/complaints', { method: 'POST', body: form })
}

// PATCH /api/complaints/:id (admin triage)
export function patchComplaint(id, { status, assigned_to, admin_notes }) {
  return request(`/complaints/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status, assigned_to, admin_notes }),
  })
}

// GET /api/complaints/admin/notifications
export function getAdminNotifications({ limit = 20 } = {}) {
  return request(`/complaints/admin/notifications?limit=${limit}`)
}

// POST /api/reports/appliance-left-on (student appliance left on signal)
export function reportApplianceLeftOn({ room_id, equipment_type, notes = '' }) {
  return post('/reports/appliance-left-on', { room_id: Number(room_id), equipment_type, notes })
}
