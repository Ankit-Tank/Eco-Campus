import { Construction } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'

// Used for sidebar items whose page is not built yet. "title" is an i18n key, e.g. "adminNav.water".
export default function AdminPlaceholder({ title }) {
  const { t } = useLanguage()
  return (
    <>
      <header className="page-head">
        <div>
          <h1>{t(title)}</h1>
        </div>
      </header>
      <div className="state-box">
        <Construction size={26} aria-hidden="true" />
        <div>
          <strong>{t('common.comingSoon')}</strong>
          <p>{t('common.comingSoonText')}</p>
        </div>
      </div>
    </>
  )
}
