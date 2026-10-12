import { useEffect, useState } from 'react'
import { User, ShieldCheck } from 'lucide-react'
import Brand from '../components/Brand.jsx'
import LanguageToggle from '../components/LanguageToggle.jsx'
import ImpactCard from '../components/ImpactCard.jsx'
import StudentLogin from '../components/auth/StudentLogin.jsx'
import AdminLogin from '../components/auth/AdminLogin.jsx'
import { getPublicImpact } from '../services/dashboardApi.js'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { ROLES } from '../config.js'
import './Login.css'

const ROLE_ICONS = { student: User, admin: ShieldCheck }

export default function Login() {
  const { t } = useLanguage()
  const [role, setRole] = useState('student')
  const [resetCount, setResetCount] = useState(0) // changing this number restarts the login form

  // status is "loading", "ready" or "error"
  const [impact, setImpact] = useState({ status: 'loading', cards: [], isSimulated: false })

  // The numbers on the side cards come from the backend, not from this file.
  useEffect(() => {
    getPublicImpact()
      .then((data) => setImpact({ status: 'ready', cards: data.cards, isSimulated: data.is_simulated }))
      .catch(() => setImpact({ status: 'error', cards: [], isSimulated: false }))
  }, [])

  // Clicking the logo goes to /login (see Brand.jsx). Here we also restart the form,
  // so someone in the middle of the OTP step goes back to the very first step.
  function handleLogoClick() {
    setRole('student')
    setResetCount(resetCount + 1)
  }

  const leftCards = impact.cards.slice(0, 2)
  const rightCards = impact.cards.slice(2, 4)

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

          {impact.isSimulated && <p className="demo-note">{t('login.demoNote')}</p>}
        </section>

        <aside className="impact-col impact-col--left" aria-label="Campus impact">
          {impact.status === 'loading' && (
            <>
              <ImpactCard loading />
              <ImpactCard loading />
            </>
          )}
          {impact.status === 'error' && <p className="impact-error">{t('login.impactUnavailable')}</p>}
          {leftCards.map((card) => (
            <ImpactCard key={card.key} card={card} />
          ))}
        </aside>

        <aside className="impact-col impact-col--right" aria-label="Campus impact, continued">
          {impact.status === 'loading' && (
            <>
              <ImpactCard loading />
              <ImpactCard loading />
            </>
          )}
          {rightCards.map((card) => (
            <ImpactCard key={card.key} card={card} />
          ))}
        </aside>
      </main>
    </div>
  )
}
