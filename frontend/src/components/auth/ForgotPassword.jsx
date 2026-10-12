import { useState } from 'react'
import { ArrowRight, CheckCircle2, Loader2 } from 'lucide-react'
import PhoneStep from './PhoneStep.jsx'
import OtpStep from './OtpStep.jsx'
import PasswordField from './PasswordField.jsx'
import WelcomeBlock from './WelcomeBlock.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { sendAdminResetOtp, verifyAdminResetOtp, resetAdminPassword } from '../../services/authApi.js'
import { getErrorMessage } from '../../utils/errors.js'
import { DEMO_ACCOUNTS, DEMO_MODE, MIN_PASSWORD_LENGTH } from '../../config.js'

// Admin "Forgot password": mobile number -> OTP -> new password -> done.
export default function ForgotPassword({ onBack }) {
  const { t } = useLanguage()

  const [step, setStep] = useState('phone') // "phone", "otp", "newPassword" or "done"
  const [phone, setPhone] = useState(DEMO_MODE ? DEMO_ACCOUNTS.admin.phone : '')
  const [otpInfo, setOtpInfo] = useState({ devOtp: null, resendAfterSeconds: 30 })
  const [resetToken, setResetToken] = useState('')

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function requestOtp(phoneNumber) {
    const result = await sendAdminResetOtp(phoneNumber)
    setOtpInfo({ devOtp: result.dev_otp || null, resendAfterSeconds: result.resend_after_seconds || 30 })
  }

  async function handlePhoneSubmit(phoneNumber) {
    await requestOtp(phoneNumber)
    setPhone(phoneNumber)
    setStep('otp')
  }

  async function handleVerify(otp) {
    const result = await verifyAdminResetOtp(phone, otp)
    setResetToken(result.reset_token)
    setStep('newPassword')
  }

  async function handleReset(event) {
    event.preventDefault()
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(t('errors.passwordShort', { min: MIN_PASSWORD_LENGTH }))
      return
    }
    if (newPassword !== confirmPassword) {
      setError(t('errors.passwordMismatch'))
      return
    }
    setSaving(true)
    setError('')
    try {
      await resetAdminPassword(resetToken, newPassword)
      setStep('done')
    } catch (err) {
      setError(getErrorMessage(err, t))
    } finally {
      setSaving(false)
    }
  }

  const backLink = (
    <div className="auth-links auth-links--center">
      <button type="button" className="link-button" onClick={onBack}>
        {t('auth.backToSignIn')}
      </button>
    </div>
  )

  if (step === 'phone') {
    return (
      <>
        <PhoneStep
          title={t('auth.resetTitle')}
          subtitle={t('auth.resetPhoneSubtitle')}
          initialPhone={phone}
          onSubmit={handlePhoneSubmit}
        />
        {backLink}
      </>
    )
  }

  if (step === 'otp') {
    return (
      <>
        <OtpStep
          phone={phone}
          devOtp={otpInfo.devOtp}
          resendAfterSeconds={otpInfo.resendAfterSeconds}
          buttonLabel={t('auth.verifyContinue')}
          onVerify={handleVerify}
          onResend={() => requestOtp(phone)}
          onChangeNumber={() => setStep('phone')}
        />
        {backLink}
      </>
    )
  }

  if (step === 'newPassword') {
    return (
      <>
        <WelcomeBlock
          title={t('auth.newPasswordTitle')}
          subtitle={t('auth.newPasswordSubtitle', { min: MIN_PASSWORD_LENGTH })}
        />
        <form className="login-form" onSubmit={handleReset} noValidate>
          <PasswordField
            id="new-password"
            label={t('auth.newPassword')}
            value={newPassword}
            onChange={setNewPassword}
            autoComplete="new-password"
          />
          <PasswordField
            id="confirm-password"
            label={t('auth.confirmPassword')}
            value={confirmPassword}
            onChange={setConfirmPassword}
            autoComplete="new-password"
          />

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="login-button" disabled={saving}>
            {saving ? (
              <>
                <Loader2 size={20} className="spin" /> {t('auth.saving')}
              </>
            ) : (
              <>
                {t('auth.resetPassword')} <ArrowRight size={20} />
              </>
            )}
          </button>
        </form>
      </>
    )
  }

  // step === 'done'
  return (
    <div className="reset-done">
      <CheckCircle2 size={64} />
      <h2>{t('auth.resetDoneTitle')}</h2>
      <p>{t('auth.resetDoneText')}</p>
      <button type="button" className="login-button" onClick={onBack}>
        {t('auth.backToSignIn')}
      </button>
    </div>
  )
}
