import { useState } from 'react'
import { User, ShieldCheck } from 'lucide-react'
import Brand from '../components/Brand.jsx'
import LanguageToggle from '../components/LanguageToggle.jsx'
import StudentLogin from '../components/auth/StudentLogin.jsx'
import AdminLogin from '../components/auth/AdminLogin.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { ROLES } from '../config.js'
import './Login.css'

const ROLE_ICONS = { student: User, admin: ShieldCheck }

export default function Login() {
  const { t } = useLanguage()
  const [role, setRole] = useState('student')
  const [resetCount, setResetCount] = useState(0) // changing this number restarts the login form

  // Clicking the logo goes to /login (see Brand.jsx). Here we also restart the form,
  // so someone in the middle of the OTP step goes back to the very first step.
  function handleLogoClick() {
    setRole('student')
    setResetCount(resetCount + 1)
  }

  return (
    <div className="login-page">
      <div className="login-bg" aria-hidden="true" />

      <header className="login-nav">
        <Brand onClick={handleLogoClick} />
        <div className="nav-right">
          <ul className="nav-words">
            <li>{t('nav.monitor')}</li>
            <li>{t('nav.understand')}</li>
            <li>{t('nav.reduce')}</li>
            <li>{t('nav.together')}</li>
          </ul>
          <LanguageToggle />
        </div>
      </header>

      <main className="login-main">
        <section className="login-hero">
          <h1>
            {t('hero.line1')}
            <br />
            {t('hero.line2Before')}
            <span className="accent">{t('hero.line2Accent')}</span>
          </h1>
          <p>{t('hero.subtitle')}</p>
        </section>

        <section className="login-card" aria-label="Sign in">
          <div className="role-tabs" role="tablist" aria-label={t('roles.chooseRole')}>
            {ROLES.map((value) => {
              const RoleIcon = ROLE_ICONS[value]
              return (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  aria-selected={role === value}
                  className="role-tab"
                  onClick={() => setRole(value)}
                >
                  <RoleIcon size={20} />
                  {t(`roles.${value}`)}
                </button>
              )
            })}
          </div>

          {/* Switching tab or pressing the logo remounts the form, so every step starts fresh */}
          <div className="auth-area" key={`${role}-${resetCount}`}>
            {role === 'student' ? <StudentLogin /> : <AdminLogin />}
          </div>
        </section>
      </main>
    </div>
  )
}
