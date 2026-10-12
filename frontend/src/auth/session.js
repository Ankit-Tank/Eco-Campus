// Remembers who is logged in, using the browser's localStorage.
import { STORAGE_KEYS } from '../config.js'

export function getToken() {
  return localStorage.getItem(STORAGE_KEYS.token)
}

export function getUser() {
  const saved = localStorage.getItem(STORAGE_KEYS.user)
  return saved ? JSON.parse(saved) : null
}

// session = { access_token, user: { id, name, role } }
export function saveSession(session) {
  localStorage.setItem(STORAGE_KEYS.token, session.access_token)
  localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(session.user))
}

// Only removes the login. The language choice stays saved.
export function logout() {
  localStorage.removeItem(STORAGE_KEYS.token)
  localStorage.removeItem(STORAGE_KEYS.user)
}
