import { API_BASE_URL } from '../config.js'
import { getToken } from '../auth/session.js'
import { request, post } from './httpClient.js'

export function getReportsSummary({ from, to } = {}) {
  const params = new URLSearchParams()
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  return request(`/reports/summary?${params.toString()}`)
}

export function reportApplianceLeftOn({ roomId, equipmentType, notes }) {
  return post('/reports/appliance-left-on', {
    room_id: roomId,
    equipment_type: equipmentType,
    notes,
  })
}

export function getExportCsvUrl({ from, to } = {}) {
  const params = new URLSearchParams()
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  return `${API_BASE_URL}/reports/export.csv?${params.toString()}`
}

export async function downloadReportCsv({ from, to, filename = 'ghostwatt_sustainability_report.csv' } = {}) {
  const params = new URLSearchParams()
  if (from) params.append('from', from)
  if (to) params.append('to', to)
  
  const token = getToken()
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(`${API_BASE_URL}/reports/export.csv?${params.toString()}`, { headers })
  if (!res.ok) throw new Error('Failed to download CSV export')
  
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}
