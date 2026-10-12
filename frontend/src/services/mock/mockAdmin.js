// FAKE DATA. Only used when VITE_USE_MOCK=true. Real numbers must come from the backend.
const wait = (ms = 450) => new Promise((resolve) => setTimeout(resolve, ms))

const ACTUAL = [400, 520, 660, 540, 420, 500, 570, 640, 520, 420, 380, 390]
const BASELINE = [450, 650, 840, 700, 580, 600, 720, 800, 850, 700, 540, 480]

const BLOCKS = [
  { key: 'academic_a', name: 'Academic Block A', share_pct: 28 },
  { key: 'academic_b', name: 'Academic Block B', share_pct: 22 },
  { key: 'hostel_1', name: 'Hostel 1', share_pct: 18 },
  { key: 'hostel_2', name: 'Hostel 2', share_pct: 12 },
  { key: 'admin', name: 'Administrative', share_pct: 10 },
  { key: 'cafeteria', name: 'Cafeteria', share_pct: 6 },
  { key: 'others', name: 'Others', share_pct: 4 },
]

const BUILDINGS = [
  { name: 'Admin', active_kw: 186, daily_var_pct: 12, status: 'exceeded' },
  { name: 'Academics', active_kw: 142, daily_var_pct: 8, status: 'normal' },
  { name: 'Hostel A', active_kw: 210, daily_var_pct: 18, status: 'exceeded' },
  { name: 'Hostel B', active_kw: 168, daily_var_pct: 6, status: 'normal' },
]

// Mirrors GET /api/dashboard/admin-overview
export async function getAdminOverview({ from, to, zone = 'all' } = {}) {
  await wait()
  const end = new Date(to)
  const series = ACTUAL.map((actual, i) => {
    const d = new Date(end)
    d.setDate(end.getDate() - (ACTUAL.length - 1 - i))
    return { date: d.toISOString().slice(0, 10), actual_kw: actual, baseline_kw: BASELINE[i] }
  })
  const total = 4980
  const picked = zone === 'all' ? BLOCKS : BLOCKS.filter((b) => b.key === zone)
  return {
    is_simulated: true,
    from,
    to,
    zones: BLOCKS.map((b) => ({ key: b.key, name: b.name })),
    kpis: { conserved_mwh: 18.4, consumption_mwh: 142.8, consumption_change_pct: -4.2, co2_saved_tonnes: 14.6 },
    series,
    optimization_events: [{ date: series[7].date }],
    blocks: picked.map((b) => ({ ...b, kwh: Math.round((total * b.share_pct) / 100) })),
    total_kwh: zone === 'all' ? total : Math.round((total * picked[0].share_pct) / 100),
    buildings: BUILDINGS,
  }
}
