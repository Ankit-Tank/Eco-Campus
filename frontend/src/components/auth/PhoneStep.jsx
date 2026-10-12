import { useState } from 'react'
import { ArrowRight, Loader2 } from 'lucide-react'
import WelcomeBlock from './WelcomeBlock.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { COUNTRY_CODE, cleanPhoneInput, isValidPhone } from '../../utils/phone.js'
import { getErrorMessage } from '../../utils/errors.js'

// Step 1 of student login and of "forgot password": ask for the mobile number.
// onSubmit(phone) should send the OTP. If it throws, the error is shown under the field.
export default function PhoneStep({ title, subtitle, initialPhone = '', onSubmit }) {
  const { t } = useLanguage()
  const [phone, setPhone] = useState(initialPhone)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!isValidPhone(phone)) {
      setError(t('errors.phoneInvalid'))
      return
    }
    setLoading(true)
    setError('')
    try {
      await onSubmit(phone)
    } catch (err) {
      setError(getErrorMessage(err, t))
      setLoading(false)
    }
  }

  return (
    <>
      <WelcomeBlock title={title} subtitle={subtitle} />
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="phone">{t('auth.mobileNumber')}</label>
          <div className="phone-wrap">
            <span className="phone-prefix">{COUNTRY_CODE}</span>
            <input
              id="phone"
              type="tel"
              inputMode="numeric"
              autoComplete="tel-national"
              value={phone}
              onChange={(e) => setPhone(cleanPhoneInput(e.target.value))}
            />
          </div>
        </div>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="login-button" disabled={loading}>
          {loading ? (
            <>
              <Loader2 size={20} className="spin" /> {t('auth.sending')}
            </>
          ) : (
            <>
              {t('auth.sendOtp')} <ArrowRight size={20} />
            </>
          )}
        </button>
      </form>
    </>
  )
}
