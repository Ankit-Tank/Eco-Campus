// Number, date and CSV helpers shared by the admin and student screens.

export const formatNumber = (n, digits = 0) => {
  if (n === null || n === undefined || isNaN(Number(n))) {
    return (0).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
  }
  return Number(n).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

const localeFor = (language) => (language === 'hi' ? 'hi-IN' : 'en-US')

// "Oct 1 - 12, 2026"  or  "Sep 28 - Oct 12, 2026"
export function formatRange(from, to, language = 'en') {
  const locale = localeFor(language)
  const a = new Date(from)
  const b = new Date(to)
  const sameMonth = a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear()
  const start = a.toLocaleDateString(locale, { month: 'short', day: 'numeric' })
  const end = b.toLocaleDateString(locale, sameMonth ? { day: 'numeric', year: 'numeric' } : { month: 'short', day: 'numeric', year: 'numeric' })
  return `${start} - ${end}`
}

// "2026-10-12" (date only) is read as a LOCAL day, so it never shifts by one day in other time zones.
const toDate = (iso) => (/^\d{4}-\d{2}-\d{2}$/.test(String(iso)) ? new Date(`${iso}T00:00:00`) : new Date(iso))

export const formatDate = (iso, language = 'en') =>
  toDate(iso).toLocaleDateString(localeFor(language), { month: 'short', day: 'numeric', year: 'numeric' })

export const formatShortDate = (iso, language = 'en') =>
  toDate(iso).toLocaleDateString(localeFor(language), { month: 'short', day: 'numeric' })

// Energy / CO2 values that are tiny in MWh or tonnes are shown in kWh / kg instead of "0.0".
export function scaleEnergyMwh(mwh) {
  const n = Number(mwh) || 0
  return n >= 1 ? { value: n, unit: 'units2.mwh' } : { value: n * 1000, unit: 'units2.kwh' }
}
export function scaleCo2Tonnes(tonnes) {
  const n = Number(tonnes) || 0
  return n >= 1 ? { value: n, unit: 'units2.tco2e' } : { value: n * 1000, unit: 'units2.kg' }
}

const toIso = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// A range of the last N days, ending on `end` (default: today). Returns { from, to } as YYYY-MM-DD.
export function lastDays(days, end = new Date()) {
  const to = new Date(end)
  const from = new Date(end)
  from.setDate(to.getDate() - (days - 1))
  return { from: toIso(from), to: toIso(to) }
}

// rows = array of arrays. Builds a CSV file in the browser and downloads it.
export function downloadCsv(filename, rows) {
  const escape = (value) => {
    const text = String(value ?? '')
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
  }
  const csv = rows.map((row) => row.map(escape).join(',')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
