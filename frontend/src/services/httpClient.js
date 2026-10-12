import { API_BASE_URL, STORAGE_KEYS } from '../config.js'
import { getToken, logout } from '../auth/session.js'

// An error that carries the backend's error "code" so we can translate it.
export class ApiError extends Error {
  constructor(message, code = 'GENERIC') {
    super(message)
    this.code = code
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

  let response
  try {
    response = await fetch(API_BASE_URL + path, { ...options, headers })
  } catch {
    throw new ApiError('Cannot reach the server. Check that the backend is running.', 'NETWORK')
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
      } else if (body.detail && !Array.isArray(body.detail)) {
        message = body.detail.message || '' // our format: { code, message }
        code = body.detail.code || 'GENERIC'
      }
    } catch {
      // No JSON in the response, so we keep the defaults.
    }
    throw new ApiError(message || 'Something went wrong. Please try again.', code)
  }

  return response.json()
}

// Shortcut for POST requests with a JSON body.
export function post(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) })
}
