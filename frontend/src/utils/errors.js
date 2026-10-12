// Turns an error into a message in the user's language.
// The backend should send errors like: { "detail": { "code": "INVALID_OTP", "message": "..." } }
// We translate by "code" (see "errors" in src/i18n/en.js) and fall back to the backend's message.
export function getErrorMessage(error, t) {
  if (error.code) {
    const key = `errors.${error.code}`
    const text = t(key)
    if (text !== key) return text // t() returns the key itself when no translation exists
  }
  return error.message || t('errors.GENERIC')
}
