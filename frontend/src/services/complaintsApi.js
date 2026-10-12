// Wraps backend/app/routes/complaints.py   (URL starts with /api/complaints)
import { request } from './httpClient.js'
import { USE_MOCK } from '../config.js'
import * as mock from './mock/mockStudent.js'

// complaint = { id, title, place, category, status, created_at, image_url }
// status = 'submitted' | 'accepted' | 'in_progress' | 'resolved' | 'rejected' | 'reopened'

// GET /api/complaints/mine   -> { items: [complaint] }   (only the logged-in student's complaints)
export function getMyComplaints() {
  if (USE_MOCK) return mock.getMyComplaints()
  return request('/complaints/mine')
}

// POST /api/complaints   (multipart/form-data)
//   fields: title, category, location, description (optional), image (optional JPG/PNG, max 5 MB)
//   -> complaint
export function createComplaint({ title, category, location, description, image }) {
  const form = new FormData()
  form.append('title', title)
  form.append('category', category)
  form.append('location', location)
  if (description) form.append('description', description)
  if (image) form.append('image', image)
  if (USE_MOCK) return mock.createComplaint(form)
  return request('/complaints', { method: 'POST', body: form })
}
