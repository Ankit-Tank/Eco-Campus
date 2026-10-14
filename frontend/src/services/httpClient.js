import { API_BASE_URL, STORAGE_KEYS } from '../config.js'
import { getToken, logout } from '../auth/session.js'

// An error that carries the backend's error "code" so we can translate it.
const REQUEST_TIMEOUT_MS = 30000

export class ApiError extends Error {
  constructor(message, code = 'GENERIC', status = 0) {
    super(message)
    this.code = code
    this.status = status // HTTP status (0 = no response, e.g. network error)
  }
}

export async function request(path, options = {}) {
  const headers = {
    // Lets the backend (for example the AI assistant) reply in the same language later.
    'Accept-Language': localStorage.getItem(STORAGE_KEYS.language) || 'en',
    ...options.headers,
  }
  // File uploads (FormData) set their own Content-Type, so only add it for JSON.
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json'

  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  // Never hang forever if the backend stalls.
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  let response
  try {
    response = await fetch(API_BASE_URL + path, { ...options, headers, signal: options.signal || controller.signal })
  } catch (err) {
    if (err?.name === 'AbortError') throw new ApiError('The server took too long to respond. Please try again.', 'TIMEOUT')
    throw new ApiError('Cannot reach the server. Check that the backend is running.', 'NETWORK')
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) {
    if (response.status === 401 && !path.includes('/auth/login') && !path.includes('/auth/student/otp') && !path.includes('/auth/admin/login')) {
      logout()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    let message = ''
    let code = 'GENERIC'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') {
        message = body.detail // plain FastAPI error: show its text
        code = null
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation error list: show the first problem in plain words
        const first = body.detail[0] || {}
        const field = Array.isArray(first.loc) ? first.loc.filter((p) => p !== 'body' && p !== 'query').join('.') : ''
        message = String(first.msg || '').replace(/^Value error, /, '')
        if (field && message) message = `${field}: ${message}`
        code = null
      } else if (body.detail && !Array.isArray(body.detail)) {
        message = body.detail.message || '' // our format: { code, message }
        code = body.detail.code || 'GENERIC'
      }
    } catch {
      // No JSON in the response, so we keep the defaults.
    }
    // The Vite dev proxy answers an empty HTTP 500 / 502 / 503 / 504 when the backend is not running
    // or listens on another port; say that instead of a vague "something went wrong".
    if (!message && [500, 502, 503, 504].includes(response.status)) {
      throw new ApiError('Cannot reach the server. Check that the backend is running and that VITE_BACKEND_URL in frontend/.env points to its port.', 'NETWORK', response.status)
    }
    throw new ApiError(message || 'Something went wrong. Please try again.', code, response.status)
  }

  if (response.status === 204) return null // e.g. DELETE: success with no body
  return response.json()
}

// Shortcut for POST requests with a JSON body.
export function post(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) })
}
