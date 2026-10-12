// Indian mobile numbers: 10 digits, starting with 6, 7, 8 or 9.
export const COUNTRY_CODE = '+91'

// Keeps only digits and stops at 10 of them.
export function cleanPhoneInput(value) {
  return value.replace(/\D/g, '').slice(0, 10)
}

export function isValidPhone(phone) {
  return /^[6-9]\d{9}$/.test(phone)
}

// What we send to the backend: +919876543210
export function toApiPhone(phone) {
  return COUNTRY_CODE + phone
}

// What we show on screen: +91 98XXXXX210
export function maskPhone(phone) {
  return `${COUNTRY_CODE} ${phone.slice(0, 2)}XXXXX${phone.slice(7)}`
}
