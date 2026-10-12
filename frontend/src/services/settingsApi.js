// Wraps backend/app/routes/app_settings.py (URL /api/settings)
import { request } from './httpClient.js'

export function getSettings() {
  return request('/settings')
}

export function updateSettings(settingsDict) {
  return request('/settings', {
    method: 'PUT',
    body: JSON.stringify({ settings: settingsDict }),
  })
}
