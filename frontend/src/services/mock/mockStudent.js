// FAKE DATA. Only used when VITE_USE_MOCK=true. Real numbers must come from the backend.
const wait = (ms = 450) => new Promise((resolve) => setTimeout(resolve, ms))

// Newest first. Added reports are kept in memory until the page is refreshed.
const complaints = [
  { id: 'C-1005', title: 'Leaking tap in Library washroom', place: 'Library', category: 'leaking_tap', status: 'accepted', created_at: '2026-10-05', image_url: null },
  { id: 'C-1004', title: 'Lights left on in Classroom 204', place: 'Classroom 204', category: 'lights_left_on', status: 'in_progress', created_at: '2026-09-28', image_url: null },
  { id: 'C-1003', title: 'AC running in empty room', place: 'Academic Block B', category: 'ac_running', status: 'accepted', created_at: '2026-09-21', image_url: null },
  { id: 'C-1002', title: 'Water wastage in garden area', place: 'Main Ground', category: 'water_wastage', status: 'rejected', created_at: '2026-09-12', image_url: null },
  { id: 'C-1001', title: 'Damaged switch panel', place: 'Hostel A', category: 'electrical_damage', status: 'in_progress', created_at: '2026-09-03', image_url: null },
]
let added = 0

// GET /api/complaints/mine
export async function getMyComplaints() {
  await wait()
  return { items: [...complaints] }
}

// POST /api/complaints   (multipart form)
export async function createComplaint(form) {
  await wait(700)
  added += 1
  const item = {
    id: `C-${1005 + added}`,
    title: form.get('title'),
    place: form.get('location'),
    category: form.get('category'),
    status: 'submitted',
    created_at: new Date().toISOString().slice(0, 10),
    image_url: form.get('image') instanceof File ? URL.createObjectURL(form.get('image')) : null,
  }
  complaints.unshift(item)
  return item
}

// GET /api/dashboard/student-home
export async function getStudentHome(user) {
  await wait()
  return {
    is_simulated: true,
    name: user?.name || 'Student',
    stats: { reports_filed: 12 + added, accepted: 8, in_progress: 3, estimated_saving_kwh: 1240 },
    recent: complaints.slice(0, 5),
    impact: { electricity_kwh: 780, water_litres: 12500, co2_kg: 620 },
  }
}
