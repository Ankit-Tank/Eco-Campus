import { AlertTriangle } from 'lucide-react'
import { useLanguage } from '../../i18n/LanguageContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'

// Shown when a request fails. "onRetry" reloads the data.
export default function ErrorState({ error, onRetry }) {
  const { t } = useLanguage()
  return (
    <div className="state-box state-box--error" role="alert">
      <AlertTriangle size={22} aria-hidden="true" />
      <div>
        <strong>{t('common.loadError')}</strong>
        <p>{error ? getErrorMessage(error, t) : ''}</p>
      </div>
      {onRetry && (
        <button type="button" className="btn btn--outline" onClick={onRetry}>
          {t('common.retry')}
        </button>
      )}
    </div>
  )
}
