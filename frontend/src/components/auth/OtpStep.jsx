import { useEffect, useState } from 'react'
import { ArrowRight, Loader2 } from 'lucide-react'
import WelcomeBlock from './WelcomeBlock.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { maskPhone } from '../../utils/phone.js'
import { getErrorMessage } from '../../utils/errors.js'
import { OTP_LENGTH } from '../../config.js'

// Step 2: type the OTP that was sent to the phone.
//   onVerify(otp)    - check the OTP. Throw an error if it is wrong.
//   onResend()       - send a new OTP.
//   onChangeNumber() - go back to the phone step.
//   devOtp           - only in demo mode: the OTP is shown on screen instead of an SMS.
export default function OtpStep({ phone, devOtp, resendAfterSeconds, buttonLabel, onVerify, onResend, onChangeNumber }) {
  const { t } = useLanguage()
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(resendAfterSeconds)

  // Counts down 1 second at a time until the resend button is available.
  useEffect(() => {
    if (secondsLeft <= 0) return
    const timer = setTimeout(() => setSecondsLeft(secondsLeft - 1), 1000)
    return () => clearTimeout(timer)
  }, [secondsLeft])

  async function handleSubmit(event) {
    event.preventDefault()
    if (otp.length !== OTP_LENGTH) {
      setError(t('errors.otpFormat'))
      return
    }
    setLoading(true)
    setError('')
    try {
      await onVerify(otp)
    } catch (err) {
      setError(getErrorMessage(err, t))
      setLoading(false)
    }
  }

  async function handleResend() {
    setError('')
    try {
      await onResend()
      setOtp('')
      setSecondsLeft(resendAfterSeconds)
    } catch (err) {
      setError(getErrorMessage(err, t))
    }
  }

  return (
    <>
      <WelcomeBlock title={t('auth.enterOtp')} subtitle={t('auth.otpSentTo', { phone: maskPhone(phone) })} />
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="otp">{t('auth.otpLabel')}</label>
          <input
            id="otp"
            className="otp-input"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={OTP_LENGTH}
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
          />
        </div>

        {devOtp && <p className="demo-otp">{t('auth.demoOtp', { otp: devOtp })}</p>}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="login-button" disabled={loading}>
          {loading ? (
            <>
              <Loader2 size={20} className="spin" /> {t('auth.verifying')}
            </>
          ) : (
            <>
              {buttonLabel} <ArrowRight size={20} />
            </>
          )}
        </button>

        <div className="auth-links">
          <button type="button" className="link-button" onClick={onChangeNumber}>
            {t('auth.changeNumber')}
          </button>
          <button type="button" className="link-button" onClick={handleResend} disabled={secondsLeft > 0}>
            {secondsLeft > 0 ? t('auth.resendIn', { seconds: secondsLeft }) : t('auth.resendOtp')}
          </button>
        </div>
      </form>
    </>
  )
}
