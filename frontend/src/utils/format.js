// Number, date and CSV helpers shared by the admin and student screens.

export const formatNumber = (n, digits = 0) =>
  Number(n).toLocaleString('en-IN', { minimumFractionDigits: digits, maximumFractionDigits: digits })

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

export const formatDate = (iso, language = 'en') =>
  new Date(iso).toLocaleDateString(localeFor(language), { month: 'short', day: 'numeric', year: 'numeric' })

export const formatShortDate = (iso, language = 'en') =>
  new Date(iso).toLocaleDateString(localeFor(language), { month: 'short', day: 'numeric' })

const toIso = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// A range of the last N days, ending today. Returns { from, to } as YYYY-MM-DD.
export function lastDays(days) {
  const to = new Date()
  const from = new Date()
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
