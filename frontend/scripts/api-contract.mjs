// Frontend <-> backend contract check.
//
// Runs the REAL service functions from src/services (the same ones the pages call) against a
// running backend, as an admin and as a student, and verifies the response fields the pages read.
//
//   1) start the backend            (cd backend && uvicorn app.main:app --port 8000)
//   2) cd frontend && npm run check:api            (BACKEND_URL=http://127.0.0.1:8001 npm run check:api for another port)
//
// It creates and removes its own test data (a temporary room, complaints, a student account) and
// changes the simulation clock, so run it against a demo database you can re-seed, not real data.

const BACKEND = process.env.BACKEND_URL || import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'

// ---- browser shims (the services expect a browser) ----
const store = new Map()
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
}
const realFetch = globalThis.fetch
globalThis.fetch = (url, opts) => realFetch(String(url).startsWith('/') ? BACKEND + url : url, opts)

const { adminLogin, sendStudentOtp, verifyStudentOtp } = await import('../src/services/authApi.js')
const { saveSession, logout } = await import('../src/auth/session.js')
const dash = await import('../src/services/dashboardApi.js')
const elec = await import('../src/services/electricityApi.js')
const ghost = await import('../src/services/ghostLoadApi.js')
const rooms = await import('../src/services/roomsApi.js')
const tt = await import('../src/services/timetableApi.js')
const sav = await import('../src/services/savingsApi.js')
const water = await import('../src/services/waterApi.js')
const comp = await import('../src/services/complaintsApi.js')
const rep = await import('../src/services/reportsApi.js')
const set = await import('../src/services/settingsApi.js')
const sim = await import('../src/services/simulatorApi.js')
const lead = await import('../src/services/leaderboardApi.js')
const ai = await import('../src/services/assistantApi.js')
const { lastDays } = await import('../src/utils/format.js')

let passed = 0
const failed = []
async function check(name, fn) {
  try {
    await fn()
    passed += 1
    console.log(`  ok   ${name}`)
  } catch (e) {
    failed.push(name)
    console.log(`  FAIL ${name}\n       ${e.message}`)
  }
}
const assert = (cond, msg) => {
  if (!cond) throw new Error(msg)
}
const has = (obj, ...keys) => {
  for (const k of keys) assert(obj && k in obj, `missing field "${k}" in ${JSON.stringify(obj)?.slice(0, 160)}`)
}
const PNG = new Blob([Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0])], { type: 'image/png' })
const rejects = async (p, status) => {
  try {
    await p
  } catch (e) {
    if (status) assert(e.status === status, `expected HTTP ${status}, got ${e.status} (${e.message})`)
    return
  }
  throw new Error('expected the request to be rejected')
}

// ---------------------------------------------------------------- admin
console.log('\nADMIN')
let admin
await check('admin login (email + password)', async () => {
  admin = await adminLogin('admin@ghostwatt.demo', 'admin123')
  has(admin, 'access_token', 'user')
  assert(admin.user.role === 'admin', 'role should be admin')
  saveSession(admin)
})
await check('wrong admin password is rejected with a readable message', async () => {
  const before = admin
  logout()
  await rejects(adminLogin('admin@ghostwatt.demo', 'definitely-wrong'), 401)
  saveSession(before)
})

await sim.resetSim('2026-10-12T08:00:00')
await check('simulator: state / reset(timestamp) / tick / appliance', async () => {
  const st = await sim.getSimState()
  has(st, 'virtual_now', 'running', 'speed')
  assert(st.virtual_now.startsWith('2026-10-12T08:00'), `reset ignored the timestamp: ${st.virtual_now}`)
  await sim.tickSim(15)
  const after = await sim.getSimState()
  assert(after.virtual_now.startsWith('2026-10-12T08:15'), `tick did not advance: ${after.virtual_now}`)
  const list = await rooms.getRooms()
  const eq = list.items[0].equipment[0]
  const r = await sim.setApplianceState({ equipment_id: eq.id, state: 'ON' })
  assert(r.state === 'ON', 'appliance state not applied')
})

const range = lastDays(14, new Date('2026-10-12T00:00:00'))
await check('overview: kpis / series / blocks / buildings / window', async () => {
  const o = await dash.getAdminOverview({ ...range, zone: 'all' })
  has(o, 'zones', 'kpis', 'series', 'optimization_events', 'blocks', 'total_kwh', 'buildings', 'window_to')
  has(o.kpis, 'conserved_mwh', 'consumption_mwh', 'consumption_change_pct', 'co2_saved_tonnes')
  has(o.series[0], 'date', 'actual_kw', 'baseline_kw')
  has(o.blocks[0], 'key', 'name', 'share_pct', 'kwh')
  has(o.buildings[0], 'name', 'active_kw', 'daily_var_pct', 'status')
  assert(['exceeded', 'normal', 'below'].includes(o.buildings[0].status), 'unexpected building status')
  const one = await dash.getAdminOverview({ ...range, zone: o.zones[0].key })
  assert(one.blocks.length === 1, 'zone filter should return a single block')
})
await check('dashboard summary + live snapshot', async () => {
  has(await dash.getDashboardSummary({}), 'actual_kwh', 'expected_kwh', 'ghost_kwh', 'water_litres', 'cost_inr')
  const s = await sim.getLiveSnapshot()
  has(s, 'virtual_now', 'total_actual_kw', 'total_expected_kw', 'total_ghost_kw', 'cost_per_hour', 'co2_per_hour', 'fan_equivalent', 'rooms', 'active_alerts')
  has(s.rooms[0], 'room_id', 'room_code', 'actual_kw', 'expected_kw', 'ghost_kw', 'status')
})
await check('electricity series + ghost load (every period the UI offers)', async () => {
  const e = await elec.getElectricitySeries({ limit: 50 })
  has(e, 'series')
  for (const period of ['day', 'week', 'month']) {
    const r = await ghost.getGhostRanking({ period })
    has(r, 'ranking', 'total_ghost_kwh')
  }
  const cur = await ghost.getGhostCurrent()
  has(cur, 'rooms')
  const sw = await ghost.getSwitchOffList()
  has(sw, 'items')
  const ex = await ghost.explainRoomGhost(1)
  has(ex, 'room_code')
})
await check('leaderboard (every period the UI offers)', async () => {
  for (const p of ['today', '7d', '14d', 'all']) has(await lead.getBlockLeaderboard(p), 'blocks')
})

await check('verified savings: switch off -> tick -> verified, and no double switch-off', async () => {
  const items = (await ghost.getSwitchOffList()).items
  assert(items.length > 0, 'the switch-off list is empty at the demo time')
  const first = items.find((i) => i.equipment_id) || items[0]
  const body = { room_id: first.room_id, equipment_id: first.equipment_id, notes: 'contract check' }
  const before = await sav.getSavingsSummary()
  const res = await sav.switchOffAppliance(body)
  has(res, 'id', 'verification_status')
  await sim.tickSim(15)
  await sim.tickSim(15)
  const after = await sav.getSavingsSummary()
  has(after, 'claimed_kwh', 'verified_kwh', 'label')
  assert(after.total_actions === before.total_actions + 1, 'action count did not increase')
  assert(after.claimed_kwh >= before.claimed_kwh, 'claimed kWh should not decrease')
  has(await sav.getSavingsRecords(), 'records')
  has(await sav.getActions({ limit: 5 }), 'actions')
  await rejects(sav.switchOffAppliance(body), 409)
})

await check('water: series / alerts / locations / triage', async () => {
  has(await water.getWaterSeries({}), 'series')
  const locs = await water.getWaterLocations()
  assert(Array.isArray(locs) && locs.length > 0 && 'name' in locs[0], 'locations should be a non-empty list')
  const a = await water.getWaterAlerts()
  has(a, 'alerts')
  if (a.alerts.length) {
    has(a.alerts[0], 'id', 'location_name', 'status', 'excess_litres', 'avg_flow_lph')
    const r = await water.patchWaterAlert(a.alerts[0].id, { status: a.alerts[0].status, inspection_notes: 'contract check' })
    has(r, 'status')
  }
})

await check('rooms & timetable: full create / edit / delete cycle', async () => {
  const code = `Z-${Math.floor(Math.random() * 900 + 100)}`
  const room = await rooms.createRoom({ room_code: code, block: 'z', name: 'Contract Room', room_type: 'classroom', capacity: 25, idle_baseline_kw: 0.2 })
  has(room, 'id', 'room_code')
  assert(room.block === 'Z', 'block should be upper-cased by the backend')
  await rooms.updateRoom(room.id, { name: 'Contract Room 2', capacity: 30 })
  const eq = await rooms.createEquipment(room.id, { kind: 'fan', rated_kw: 0.075, count: 4, expected_in_class: 1 })
  await rooms.updateEquipment(eq.id, { count: 6 })
  const cls = await tt.createTimetableEntry({ room_id: room.id, day_of_week: 2, start_time: '10:00', end_time: '11:30', activity: 'Contract class', expected_students: 20 })
  await tt.updateTimetableEntry(cls.id, { activity: 'Contract class 2' })
  const listed = await tt.getTimetable({ room_id: room.id })
  assert(listed.items.length === 1 && listed.items[0].activity === 'Contract class 2', 'timetable edit not reflected')
  await rejects(tt.createTimetableEntry({ room_id: room.id, day_of_week: 2, start_time: '25:99', end_time: '26:00', activity: 'x', expected_students: 1 }), 422)
  assert((await tt.deleteTimetableEntry(cls.id)) === null, 'DELETE should return no body')
  await rooms.deleteEquipment(eq.id)
  const fetched = await rooms.getRoom(room.id)
  assert(fetched.name === 'Contract Room 2' && fetched.equipment.length === 0, 'room edit / equipment delete not reflected')
  await rooms.deleteRoom(room.id)
  await rejects(rooms.getRoom(room.id), 404)
  await rejects(rooms.deleteRoom(1), 409) // a room with meter history cannot be erased
})

await check('settings: read, write, and rejection of bad numbers', async () => {
  const cur = await set.getSettings()
  has(cur.settings, 'electricity_price_per_kwh', 'emissions_factor_kg_per_kwh', 'fan_watt_equivalent', 'bucket_litres', 'water_night_threshold_lph', 'water_low_flow_baseline_lph')
  await set.updateSettings(cur.settings)
  await rejects(set.updateSettings({ ...cur.settings, bucket_litres: 'nan' }), 422)
  await rejects(set.updateSettings({ ...cur.settings, electricity_price_per_kwh: '-3' }), 422)
})
await check('reports: summary + csv url', async () => {
  const r = await rep.getReportsSummary({ from: range.from, to: range.to })
  assert(typeof r === 'object' && Object.keys(r).length > 3, 'empty report')
  assert(rep.getExportCsvUrl({ from: range.from, to: range.to }).includes('/reports/export.csv'), 'bad CSV url')
})

// ---------------------------------------------------------------- student
console.log('\nSTUDENT')
const adminSession = admin
let student
let complaintId
const phone = `98${String(Date.now()).slice(-8)}`
await check('student OTP login creates their own account', async () => {
  logout()
  const sent = await sendStudentOtp(phone)
  has(sent, 'dev_otp', 'resend_after_seconds')
  student = await verifyStudentOtp(phone, sent.dev_otp)
  assert(student.user.role === 'student', 'role should be student')
  assert(student.user.id !== adminSession.user.id, 'must be a different account')
  saveSession(student)
  await rejects(verifyStudentOtp(phone, '000000'), 400)
})
await check('student home starts at zero (nothing invented)', async () => {
  const h = await dash.getStudentHome(student.user)
  has(h, 'name', 'stats', 'recent', 'impact')
  assert(h.stats.reports_filed === 0 && h.recent.length === 0 && h.impact.electricity_kwh === 0, JSON.stringify(h))
})
await check('student files a complaint (every category the form offers) with a photo', async () => {
  const issueTypes = ['leaking_tap', 'broken_pipe', 'overflowing_tank', 'low_pressure', 'water_wastage', 'lights_left_on', 'ac_running', 'electrical_damage', 'other']
  for (const category of issueTypes) {
    const c = await comp.createComplaint({ title: `Contract ${category}`, category, building: 'Block A', location: 'Block A - Washroom', description: 'details', image: category === 'leaking_tap' ? new File([PNG], 'leak.png', { type: 'image/png' }) : undefined })
    has(c, 'id', 'complaint_code', 'status', 'history')
    if (category === 'leaking_tap') {
      complaintId = c.id
      assert(c.image_url && c.image_url.startsWith('/uploads/complaints/'), `bad image_url ${c.image_url}`)
      const img = await fetch(c.image_url)
      assert(img.status === 200, 'uploaded photo is not downloadable')
    }
  }
  const mine = await comp.getMyComplaints()
  assert(mine.items.length === issueTypes.length, `expected ${issueTypes.length} complaints, got ${mine.items.length}`)
  has(mine.items[0], 'id', 'title', 'place', 'status', 'created_at', 'history')
})
await check('student cannot reach admin data', async () => {
  // The complaints list is allowed for students but scoped: they only ever see their own.
  const visible = await comp.getComplaints({})
  assert(visible.complaints.every((c) => c.student_id === student.user.id), 'a student can see another student\'s complaint')
  await rejects(comp.getAssignees(), 403)
  await rejects(comp.getAdminNotifications(), 403)
  await rejects(sim.resetSim('2026-10-01T00:00:00'), 403)
  await rejects(rooms.createRoom({ room_code: 'S-1', block: 'S', name: 'nope', room_type: 'classroom', capacity: 5, idle_baseline_kw: 0.1 }), 403)
})
await check('student read-only campus data, leaderboard, assistant, signal', async () => {
  has(await sim.getLiveSnapshot(), 'total_ghost_kw', 'rooms')
  has(await sav.getSavingsSummary(), 'verified_kwh')
  has(await water.getWaterAlerts(), 'alerts')
  has(await lead.getBlockLeaderboard('7d'), 'blocks')
  const a = await ai.askAssistant('Which room wasted the most electricity today?')
  has(a, 'answer')
  assert(a.answer.length > 10, 'empty assistant answer')
  const rl = await rep.reportApplianceLeftOn({ roomId: 1, equipmentType: 'Fans', notes: 'contract check' })
  has(rl, 'complaint_code')
})

// ---------------------------------------------------------------- admin triage <-> student tracking
console.log('\nTRIAGE')
await check('admin assigns + resolves; student sees history and reopens', async () => {
  const studentSession = student
  saveSession(adminSession)
  const list = await comp.getComplaints({})
  has(list, 'complaints', 'overdue_count', 'frequently_affected_locations')
  const staff = (await comp.getAssignees()).assignees
  assert(staff.length > 0, 'no assignable staff')
  const assigned = await comp.patchComplaint(complaintId, { status: 'assigned', assigned_to: staff[0].id, notes: 'Plumber dispatched' })
  assert(assigned.status === 'assigned' && assigned.assigned_to === staff[0].id, 'assignment not saved')
  const notes = await comp.getAdminNotifications({ limit: 50 })
  has(notes, 'notifications', 'unread_count')
  assert(notes.unread_count > 0, 'new complaints should create unread notifications')
  await comp.markNotificationRead(notes.notifications[0].id)
  await comp.markAllNotificationsRead()
  assert((await comp.getAdminNotifications()).unread_count === 0, 'notifications were not marked read')
  await comp.patchComplaint(complaintId, { status: 'resolved', resolution_notes: 'Washer replaced' })

  saveSession(studentSession)
  const mine = (await comp.getMyComplaints()).items.find((c) => c.id === complaintId)
  assert(mine.status === 'resolved', 'student should see the resolved status')
  assert(mine.history.length >= 3, `history should show every change, got ${mine.history.length}`)
  const reopened = await comp.reopenComplaint(complaintId, 'Dripping again')
  assert(reopened.status === 'reopened', 'complaint should be reopened')
  await rejects(comp.reopenComplaint(complaintId, 'twice'), 400)
})

// cleanup: put the simulator back where a demo expects it
saveSession(adminSession)
await sim.resetSim('2026-10-12T00:00:00')

console.log(`\n${passed} passed, ${failed.length} failed`)
if (failed.length) {
  console.log('Failed: ' + failed.join(' | '))
  process.exit(1)
}
