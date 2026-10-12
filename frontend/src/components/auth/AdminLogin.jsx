import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Loader2 } from 'lucide-react'
import WelcomeBlock from './WelcomeBlock.jsx'
import PasswordField from './PasswordField.jsx'
import ForgotPassword from './ForgotPassword.jsx'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { adminLogin } from '../../services/authApi.js'
import { ApiError } from '../../services/httpClient.js'
import { saveSession } from '../../auth/session.js'
import { getErrorMessage } from '../../utils/errors.js'
import { DEMO_ACCOUNTS, DEMO_MODE } from '../../config.js'

// Admin login: email + password, with a "Forgot password?" link.
export default function AdminLogin() {
  const { t } = useLanguage()
  const navigate = useNavigate()

  const [view, setView] = useState('login') // "login" or "forgot"
  const [email, setEmail] = useState(DEMO_MODE ? DEMO_ACCOUNTS.admin.email : '')
  const [password, setPassword] = useState(DEMO_MODE ? DEMO_ACCOUNTS.admin.password : '')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!email || !password) {
      setError(t('errors.loginMissing'))
      return
    }
    setLoading(true)
    setError('')
    try {
      const session = await adminLogin(email, password)
      if (session.user.role !== 'admin') throw new ApiError('Wrong role', 'WRONG_ROLE')
      saveSession(session)
      navigate('/dashboard')
    } catch (err) {
      setError(getErrorMessage(err, t))
      setLoading(false)
    }
  }

  if (view === 'forgot') {
    return <ForgotPassword onBack={() => setView('login')} />
  }

  return (
    <>
      <WelcomeBlock title={t('auth.welcome')} subtitle={t('auth.adminSubtitle')} />
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <label htmlFor="email">{t('auth.email')}</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <PasswordField
          id="password"
          label={t('auth.password')}
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
        />

        <div className="auth-links auth-links--end">
          <button type="button" className="link-button" onClick={() => setView('forgot')}>
            {t('auth.forgotPassword')}
          </button>
        </div>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="login-button" disabled={loading}>
          {loading ? (
            <>
              <Loader2 size={20} className="spin" /> {t('auth.signingIn')}
            </>
          ) : (
            <>
              {t('auth.signInAdmin')} <ArrowRight size={20} />
            </>
          )}
        </button>
      </form>
    </>
  )
}
