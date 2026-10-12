import { useNavigate } from 'react-router-dom'
import LanguageToggle from '../components/LanguageToggle.jsx'
import { useLanguage } from '../i18n/LanguageContext.jsx'
import { getUser, logout } from '../auth/session.js'
import { APP_NAME } from '../config.js'

// PLACEHOLDER. Replace this with the real dashboard (Sidebar + Topbar + cards + charts).
// The language toggle is here to show that the language chosen on the login page is kept.
// In the real dashboard, put <LanguageToggle /> in the Topbar.
export default function Dashboard() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const user = getUser()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <main style={{ padding: 40 }}>
      <LanguageToggle />
      <h1 style={{ marginTop: 24 }}>{t('dashboard.title', { app: APP_NAME })}</h1>
      <p>{t('dashboard.signedInAs', { name: user?.name, role: t(`roles.${user?.role}`) })}</p>
      <p>{t('dashboard.placeholder')}</p>
      <button type="button" onClick={handleLogout}>
        {t('dashboard.logout')}
      </button>
    </main>
  )
}
