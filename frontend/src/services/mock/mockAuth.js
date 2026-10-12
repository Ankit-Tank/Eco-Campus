// FAKE LOGIN. Only used when VITE_USE_MOCK=true, so you can build without the backend.
// In mock mode the OTP is always 123456 and it is shown on screen.
import { ApiError } from '../httpClient.js'
import { DEMO_ACCOUNTS } from '../../config.js'

const MOCK_OTP = '123456'
const wait = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms))

let adminPassword = DEMO_ACCOUNTS.admin.password // changes when you "reset" it in mock mode

const STUDENT = { id: 1, name: 'Demo Student', role: 'student' }
const ADMIN = { id: 2, name: 'Demo Admin', role: 'admin' }

export async function sendOtp() {
  await wait()
  return { resend_after_seconds: 30, dev_otp: MOCK_OTP }
}

export async function verifyStudentOtp(phone, otp) {
  await wait()
  if (otp !== MOCK_OTP) throw new ApiError('Wrong OTP', 'INVALID_OTP')
  return { access_token: 'mock-student-token', user: STUDENT }
}

export async function adminLogin(email, password) {
  await wait()
  if (email !== DEMO_ACCOUNTS.admin.email || password !== adminPassword) {
    throw new ApiError('Wrong login', 'INVALID_CREDENTIALS')
  }
  return { access_token: 'mock-admin-token', user: ADMIN }
}

export async function verifyAdminResetOtp(phone, otp) {
  await wait()
  if (phone !== DEMO_ACCOUNTS.admin.phone || otp !== MOCK_OTP) throw new ApiError('Wrong OTP', 'INVALID_OTP')
  return { reset_token: 'mock-reset-token' }
}

export async function resetAdminPassword(resetToken, newPassword) {
  await wait()
  if (resetToken !== 'mock-reset-token') throw new ApiError('Expired', 'RESET_SESSION_EXPIRED')
  adminPassword = newPassword
  return { message: 'Password updated' }
}
