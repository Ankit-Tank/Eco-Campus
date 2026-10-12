// Small settings in one place. (The backend equivalent is backend/app/core/config.py)

export const APP_NAME = 'EcoCampus'

// Read from the .env file. See .env.example
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// Roles. The visible names ("User", "Admin") live in src/i18n so they can be translated.
export const ROLES = ['student', 'admin']

// These rules must match the backend (backend/app/core/security.py and schemas/)
export const OTP_LENGTH = 6
export const MIN_PASSWORD_LENGTH = 8

// Names used in the browser's localStorage
export const STORAGE_KEYS = {
  token: 'ec_token',
  user: 'ec_user',
  language: 'ec_language',
}

// Demo accounts. They are only pre-filled when VITE_DEMO_MODE=true.
// backend/scripts/seed.py must create users with exactly these values.
export const DEMO_ACCOUNTS = {
  student: { phone: '9876543210' },
  admin: { email: 'admin@ecocampus.demo', password: 'admin123', phone: '9876500000' },
}
