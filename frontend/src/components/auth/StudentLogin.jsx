import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PhoneStep from './PhoneStep.jsx'
import OtpStep from './OtpStep.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { sendStudentOtp, verifyStudentOtp } from '../../services/authApi.js'
import { ApiError } from '../../services/httpClient.js'
import { saveSession } from '../../auth/session.js'
import { DEMO_ACCOUNTS, DEMO_MODE } from '../../config.js'

// Student login: mobile number -> OTP -> dashboard. No email or password.
export default function StudentLogin() {
  const { t } = useLanguage()
  const navigate = useNavigate()

  const [step, setStep] = useState('phone') // "phone" or "otp"
  const [phone, setPhone] = useState(DEMO_MODE ? DEMO_ACCOUNTS.student.phone : '')
  const [otpInfo, setOtpInfo] = useState({ devOtp: null, resendAfterSeconds: 30 })

  // Asks the backend to send an OTP and remembers what it replied.
  async function requestOtp(phoneNumber) {
    const result = await sendStudentOtp(phoneNumber)
    setOtpInfo({ devOtp: result.dev_otp || null, resendAfterSeconds: result.resend_after_seconds || 30 })
  }

  async function handlePhoneSubmit(phoneNumber) {
    await requestOtp(phoneNumber)
    setPhone(phoneNumber)
    setStep('otp')
  }

  async function handleVerify(otp) {
    const session = await verifyStudentOtp(phone, otp)
    if (session.user.role !== 'student') throw new ApiError('Wrong role', 'WRONG_ROLE')
    saveSession(session)
    navigate('/dashboard')
  }

  if (step === 'phone') {
    return (
      <PhoneStep
        title={t('auth.welcome')}
        subtitle={t('auth.studentSubtitle')}
        initialPhone={phone}
        onSubmit={handlePhoneSubmit}
      />
    )
  }

  return (
    <OtpStep
      phone={phone}
      devOtp={otpInfo.devOtp}
      resendAfterSeconds={otpInfo.resendAfterSeconds}
      buttonLabel={t('auth.verifyContinue')}
      onVerify={handleVerify}
      onResend={() => requestOtp(phone)}
      onChangeNumber={() => setStep('phone')}
    />
  )
}
