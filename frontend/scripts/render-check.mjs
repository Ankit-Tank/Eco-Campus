// Mounts every page in a jsdom browser against a RUNNING backend and checks that it renders real data
// without crashing or showing the error box.
//
//   npm run check:render      (BACKEND_URL=http://127.0.0.1:8001 npm run check:render for another port)
//
// It is not a visual test (no screenshots); it proves that each page, given the backend's real responses,
// mounts, finishes loading, shows its content and logs no React errors.

import { JSDOM } from 'jsdom'

const BACKEND = process.env.BACKEND_URL || import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'

const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', { url: 'http://localhost:5173/', pretendToBeVisual: true })
const g = globalThis
for (const key of ['window', 'document', 'navigator', 'HTMLElement', 'Element', 'Node', 'MutationObserver', 'getComputedStyle', 'localStorage', 'Event', 'CustomEvent', 'HTMLInputElement', 'SVGElement']) {
  if (!(key in g) || key === 'localStorage') {
    try {
      Object.defineProperty(g, key, { value: dom.window[key], configurable: true, writable: true })
    } catch {
      /* some globals (navigator) are read-only on newer Node: ignore */
    }
  }
}
g.window = dom.window
g.document = dom.window.document
g.requestAnimationFrame = (cb) => setTimeout(cb, 0)
g.cancelAnimationFrame = (id) => clearTimeout(id)
dom.window.requestAnimationFrame = g.requestAnimationFrame
class RO { observe() {} unobserve() {} disconnect() {} }
g.ResizeObserver = RO
dom.window.ResizeObserver = RO
dom.window.matchMedia = dom.window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }))
dom.window.scrollTo = () => {}
dom.window.HTMLElement.prototype.scrollIntoView = () => {} // not implemented in jsdom
g.IS_REACT_ACT_ENVIRONMENT = true

const realFetch = g.fetch
g.fetch = (url, opts) => realFetch(String(url).startsWith('/') ? BACKEND + url : url, opts)

// capture React / runtime errors
const errors = []
const origError = console.error
console.error = (...args) => {
  const text = args.map((a) => (a instanceof Error ? a.message : String(a))).join(' ')
  if (!/not wrapped in act|Not implemented: (navigation|window\.scrollTo)|ReactDOMTestUtils/.test(text)) errors.push(text.slice(0, 300))
}

const React = (await import('react')).default
const { act } = await import('react')
const { createRoot } = await import('react-dom/client')
const { MemoryRouter } = await import('react-router-dom')
const { LanguageProvider } = await import('../src/i18n/LanguageContext.jsx')
const { adminLogin, sendStudentOtp, verifyStudentOtp } = await import('../src/services/authApi.js')
const { saveSession } = await import('../src/auth/session.js')
const sim = await import('../src/services/simulatorApi.js')
const comp = await import('../src/services/complaintsApi.js')

const pages = {
  admin: {
    'Overview': '../src/pages/admin/AdminOverview.jsx',
    'Electricity': '../src/pages/admin/AdminElectricity.jsx',
    'Water': '../src/pages/admin/AdminWater.jsx',
    'Alerts': '../src/pages/admin/AdminAlerts.jsx',
    'Maintenance': '../src/pages/admin/AdminMaintenance.jsx',
    'Rooms & Timetable': '../src/pages/admin/AdminRooms.jsx',
    'Reports': '../src/pages/admin/AdminReports.jsx',
    'Simulator': '../src/pages/admin/AdminSimulator.jsx',
    'Settings': '../src/pages/admin/AdminSettings.jsx',
    'Leaderboard': '../src/pages/LeaderboardView.jsx',
  },
  student: {
    'Home': '../src/pages/student/StudentHome.jsx',
    'Chat': '../src/pages/student/StudentChat.jsx',
    'My Reports': '../src/pages/student/StudentMyReports.jsx',
    'Campus Live': '../src/pages/student/StudentCampus.jsx',
    'Impact': '../src/pages/student/StudentImpact.jsx',
    'Leaderboard': '../src/pages/LeaderboardView.jsx',
  },
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let passed = 0
const failed = []

async function renderPage(name, path, expectText) {
  const mod = await import(/* @vite-ignore */ new URL(path, import.meta.url).pathname)
  const Page = mod.default
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const before = errors.length
  await act(async () => {
    root.render(React.createElement(LanguageProvider, null, React.createElement(MemoryRouter, null, React.createElement(Page))))
  })
  // wait (up to 12s) until loading placeholders are gone
  let waited = 0
  while (waited < 12000) {
    await act(async () => { await sleep(250) })
    waited += 250
    const busy = container.querySelector('[aria-busy="true"]')
    if (!busy && container.textContent.trim().length > 40) break
  }
  await act(async () => { await sleep(300) })
  const text = container.textContent
  const problems = []
  if (container.querySelector('.state-box--error')) problems.push('error box shown: ' + container.querySelector('.state-box--error').textContent.slice(0, 120))
  if (container.querySelector('[aria-busy="true"]')) problems.push('still loading after 12s')
  if (text.trim().length < 40) problems.push('page is (almost) empty')
  if (/\bNaN\b|undefined|\[object Object\]/.test(text)) problems.push('contains NaN / undefined / [object Object]: ' + (text.match(/.{20}(NaN|undefined|\[object Object\]).{20}/) || [''])[0])
  if (/\b(admin|student|campus|rooms|maint|buildingField)\.[a-zA-Z]+\b/.test(text) && /(rooms|campus|maint|buildingField)\.[a-z]+/i.test(text)) problems.push('untranslated i18n key visible')
  if (expectText && !expectText.test(text)) problems.push(`expected text ${expectText} not found`)
  const newErrors = errors.slice(before)
  if (newErrors.length) problems.push('console.error: ' + newErrors[0])
  await act(async () => { root.unmount() })
  container.remove()
  if (problems.length) {
    failed.push(name)
    console.log(`  FAIL ${name}\n       ${problems.join('\n       ')}`)
  } else {
    passed += 1
    console.log(`  ok   ${name}  (${text.length} chars)`)
  }
}

// Mounts a page, runs `steps(container)` (clicks etc.) and returns the final text.
async function interact(name, path, steps, expectText) {
  const Page = (await import(/* @vite-ignore */ new URL(path, import.meta.url).pathname)).default
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  const before = errors.length
  await act(async () => {
    root.render(React.createElement(LanguageProvider, null, React.createElement(MemoryRouter, null, React.createElement(Page))))
  })
  for (let i = 0; i < 40 && (container.querySelector('[aria-busy="true"]') || container.textContent.length < 40); i++) await act(async () => { await sleep(250) })
  const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); await sleep(900) }) }
  const problems = []
  try {
    const waitFor = async (find, label) => {
      for (let i = 0; i < 40; i++) {
        const el = find()
        if (el) return el
        await act(async () => { await sleep(250) })
      }
      throw new Error(`timed out waiting for ${label}`)
    }
    await steps({ container, click, waitFor })
  } catch (e) {
    problems.push('step failed: ' + e.message)
  }
  const text = container.textContent
  if (!expectText.test(text)) problems.push(`expected text ${expectText} not found after interaction`)
  const newErrors = errors.slice(before)
  if (newErrors.length) problems.push('console.error: ' + newErrors[0])
  await act(async () => { root.unmount() })
  container.remove()
  if (problems.length) { failed.push(name); console.log(`  FAIL ${name}\n       ${problems.join('\n       ')}`) } else { passed += 1; console.log(`  ok   ${name}`) }
}

// ---------- admin ----------
console.log('\nADMIN PAGES')
const admin = await adminLogin('admin@ghostwatt.demo', 'admin123')
saveSession(admin)
await sim.resetSim('2026-10-12T09:30:00')
for (let i = 0; i < 4; i++) await sim.tickSim(15)
const expectations = {
  'Overview': /MWh|kWh/, 'Electricity': /Ghost|kW/i, 'Water': /L\/h|litre|Leak/i, 'Alerts': /Verif/i,
  'Maintenance': /Complaints Queue/, 'Rooms & Timetable': /A-101/, 'Reports': /Sustainability/i, 'Simulator': /Simulator/i,
  'Settings': /Tariff|Electricity/i, 'Leaderboard': /Block/i,
}
for (const [name, path] of Object.entries(pages.admin)) await renderPage('admin / ' + name, path, expectations[name])

// ---------- student ----------
console.log('\nSTUDENT PAGES')
const phone = `97${String(Date.now()).slice(-8)}`
const sent = await sendStudentOtp(phone)
const student = await verifyStudentOtp(phone, sent.dev_otp)
saveSession(student)
await comp.createComplaint({ title: 'Render check tap', category: 'leaking_tap', building: 'Block A', location: 'Block A - Washroom', description: 'drip' })
const sexp = { 'Home': /./, 'Chat': /./, 'My Reports': /Render check tap/, 'Campus Live': /Ghost load|kW/i, 'Impact': /./, 'Leaderboard': /Block/i }
for (const [name, path] of Object.entries(pages.student)) await renderPage('student / ' + name, path, sexp[name])

console.log('\nINTERACTIONS')
await interact('student: open a report -> status history + photo area', '../src/pages/student/StudentMyReports.jsx', async ({ container, click, waitFor }) => {
  const row = await waitFor(() => container.querySelector('.report-row--button'), 'an expandable report row')
  await click(row)
}, /Status history/)

saveSession(admin)
await interact('admin: open a room -> equipment + weekly timetable', '../src/pages/admin/AdminRooms.jsx', async ({ container, click, waitFor }) => {
  const toggle = await waitFor(() => container.querySelector('button[aria-expanded="false"]'), 'a room expand button')
  await click(toggle)
}, /Weekly timetable/)
await interact('admin: add-room form opens and validates its fields', '../src/pages/admin/AdminRooms.jsx', async ({ container, click, waitFor }) => {
  const add = await waitFor(() => [...container.querySelectorAll('button')].find((b) => /Add room/.test(b.textContent)), 'the Add room button')
  await click(add)
  if (!container.querySelector('#room-code')) throw new Error('room form not shown')
}, /Idle baseline/)
await interact('admin: maintenance ticket modal shows the assignee dropdown', '../src/pages/admin/AdminMaintenance.jsx', async ({ container, click, waitFor }) => {
  const review = await waitFor(() => [...container.querySelectorAll('button')].find((b) => /Review/.test(b.textContent)), 'a complaint to review')
  await click(review)
  if (!container.querySelector('#patch-assignee')) throw new Error('assignee dropdown missing')
}, /Assign to/)

saveSession(admin)
await sim.resetSim('2026-10-12T00:00:00')
console.error = origError
console.log(`\n${passed} passed, ${failed.length} failed`)
if (failed.length) {
  console.log('Failed: ' + failed.join(' | '))
  process.exit(1)
}
process.exit(0)
