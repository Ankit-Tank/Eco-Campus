// Wraps backend/app/routes/auth.py
import { post } from './httpClient.js'
import { toApiPhone } from '../utils/phone.js'
import { USE_MOCK } from '../config.js'
import * as mock from './mock/mockAuth.js'

// ----- Student: mobile number + OTP -----

// POST /api/auth/student/otp/send    { phone }
//   -> { resend_after_seconds, dev_otp? }
export function sendStudentOtp(phone) {
  if (USE_MOCK) return mock.sendOtp(phone)
  return post('/auth/student/otp/send', { phone: toApiPhone(phone) })
}

// POST /api/auth/student/otp/verify  { phone, otp }
//   -> { access_token, user: { id, name, role } }
export function verifyStudentOtp(phone, otp) {
  if (USE_MOCK) return mock.verifyStudentOtp(phone, otp)
  return post('/auth/student/otp/verify', { phone: toApiPhone(phone), otp })
}

// ----- Admin: email + password -----

// POST /api/auth/admin/login  { email, password }
//   -> { access_token, user: { id, name, role } }
export function adminLogin(email, password) {
  if (USE_MOCK) return mock.adminLogin(email, password)
  return post('/auth/admin/login', { email, password })
}

// ----- Admin: forgot password (mobile number -> OTP -> new password) -----

// POST /api/auth/admin/forgot-password/send-otp   { phone }
//   -> { resend_after_seconds, dev_otp? }
export function sendAdminResetOtp(phone) {
  if (USE_MOCK) return mock.sendOtp(phone)
  return post('/auth/admin/forgot-password/send-otp', { phone: toApiPhone(phone) })
}

// POST /api/auth/admin/forgot-password/verify-otp  { phone, otp }
//   -> { reset_token }
export function verifyAdminResetOtp(phone, otp) {
  if (USE_MOCK) return mock.verifyAdminResetOtp(phone, otp)
  return post('/auth/admin/forgot-password/verify-otp', { phone: toApiPhone(phone), otp })
}

// POST /api/auth/admin/forgot-password/reset  { reset_token, new_password }
//   -> { message }
export function resetAdminPassword(resetToken, newPassword) {
  if (USE_MOCK) return mock.resetAdminPassword(resetToken, newPassword)
  return post('/auth/admin/forgot-password/reset', { reset_token: resetToken, new_password: newPassword })
}
